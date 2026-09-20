"""Samoaktualizácia hubu: pullni kód, a keď sa zmenil, skonči — reštart ťa zdvihne nový.

    updater = Updater(state, interval=300, max_wait=0)
    updater.start()          # vlákno vedľa uvicornu

Hub v kontajneri nemá kto aktualizovať: image má kód zapečený, takže `git pull` na
hostiteľovi mu je na nič a rebuild musí niekto spustiť. Preto si kód berie z vlastného
klonu (`docker/hub-entrypoint.sh` ho vyrobí vo volume) a tento watcher ho drží aktuálny:

1. každých `interval` sekúnd **fetch + reset** na `origin/<branch>` (klon je jednorazový,
   nikto doň ručne nesiaha — preto reset, nie rebase),
2. keď sa `HEAD` zmenil, čaká, **kým nič nepočíta** (žiadny výpočet v stave `assigned`,
   `running` ani `cancelling`; čo čaká vo fronte, reštart prežije v `state.json`),
3. potom proces **skončí** — `restart: unless-stopped` ho zdvihne na novom kóde.

Výpadok je pár sekúnd: agenti heartbeat zopakujú a keď ich hub medzitým zabudne, sami sa
prihlásia znova (`HubAgent._heartbeat`). Čo bolo rozpočítané, nikto nestratí — stav je po
každej zmene na disku.

`max_wait` je poistka pre hub, na ktorom sa stále niečo počíta: po toľkých sekundách
čakania sa reštartuje aj tak. 0 = čakaj, koľko treba.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from typing import Any, Callable

from tradebot.core.paths import REPO

from . import gitcode
from . import protocol as P

__all__ = ["Updater", "DEFAULT_INTERVAL"]

log = logging.getLogger(__name__)

#: Ako často sa pozrieť, či je nový kód.
DEFAULT_INTERVAL = 300.0
#: Koľko sekúnd sa čaká na slušné ukončenie, než proces skončí natvrdo.
SHUTDOWN_GRACE = 30.0
#: Stavy, pri ktorých by reštart niečo prerušil — `queued` ho prežije v `state.json`.
BUSY_STATES = tuple(s for s in P.LIVE_STATES if s != "queued")


def fast_forward(branch: str = "main") -> dict[str, Any]:
    """`git fetch --depth 1` + `reset --hard` na `origin/<branch>`.

    Klon hubu je jednorazový (vzniká pri prvom štarte kontajnera a nikto doň nepíše),
    takže sa neriešia lokálne zmeny — a keďže je plytký, `pull --ff-only` by na ňom
    neprešiel: nový commit nemá v tomto klone spoločného predka.
    """
    try:
        f = subprocess.run(["git", "fetch", "--depth", "1", "origin", branch], cwd=str(REPO),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=180)
        if f.returncode != 0:
            return {"ok": False, "output": (f.stderr or f.stdout).strip()[-300:]}
        r = subprocess.run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=str(REPO),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60)
        return {"ok": r.returncode == 0, "output": (r.stdout + r.stderr).strip()[-300:]}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "output": f"{type(exc).__name__}: {exc}"}


def _quit() -> None:
    """Slušne ukonči uvicorn (SIGINT), a keby sa nechcel, natvrdo — kontajner musí spadnúť,
    inak ho `restart: unless-stopped` nezdvihne na novom kóde."""
    import signal

    def natvrdo() -> None:
        time.sleep(SHUTDOWN_GRACE)
        log.warning("hub: server sa neukoncil do %.0f s, koncim natvrdo", SHUTDOWN_GRACE)
        os._exit(0)

    threading.Thread(target=natvrdo, name="hub-update-kill", daemon=True).start()
    try:
        signal.raise_signal(signal.SIGINT)
    except (AttributeError, OSError):  # noqa: BLE001 - keď sa signál nedá poslať, ide sa natvrdo
        os._exit(0)


class Updater:
    def __init__(self, state: Any, *, interval: float = DEFAULT_INTERVAL, branch: str = "main",
                 max_wait: float = 0.0, clock: Callable[[], float] = time.time,
                 pull: Callable[[], dict[str, Any]] | None = None,
                 version: Callable[[], str] | None = None,
                 quit: Callable[[], None] = _quit) -> None:
        self.state = state
        self.interval = max(30.0, float(interval))
        self.branch = branch
        self.max_wait = max(0.0, float(max_wait))
        self.clock = clock
        self.pull = pull or (lambda: fast_forward(self.branch))
        self.version = version or gitcode.version
        self.quit = quit
        self.start_version = self.version()
        #: Nový commit, na ktorý sa čaká, a odkedy sa naň čaká.
        self.pending: str | None = None
        self.pending_since: float | None = None
        self.last_error: str | None = None
        self._cakam_hlasene = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="hub-update", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                if self.tick():
                    return
            except Exception as exc:  # noqa: BLE001 - aktualizácia nesmie zhodiť hub
                self.last_error = f"{type(exc).__name__}: {exc}"
                log.warning("hub: aktualizacia zlyhala: %s", self.last_error)

    # -- jeden krok --------------------------------------------------------- #

    def busy(self) -> list[str]:
        """Výpočty, ktoré by reštart prerušil (fronta ho prežije v `state.json`)."""
        return [j["id"] for j in self.state.jobs.values()
                if j["status"] in BUSY_STATES]

    def tick(self) -> bool:
        """Jedno kolo; `True`, keď sa hub ide reštartovať."""
        if self.pending is None:
            r = self.pull()
            self.last_error = None if r.get("ok") else str(r.get("output") or "")
            if self.last_error:
                log.warning("hub: git fetch zlyhal: %s", self.last_error)
            nova = self.version()
            if not nova or nova == self.start_version:
                return False
            self.pending, self.pending_since = nova, self.clock()
            log.info("hub: novy kod %s -> %s", self.start_version or "?", nova)
        cakaju = self.busy()
        if cakaju and not self._cakalo_sa_dost():
            if not self._cakam_hlasene:
                log.info("hub: novy kod %s caka, kym dobehne %d vypoctov", self.pending, len(cakaju))
                self._cakam_hlasene = True
            return False
        log.info("hub: restartujem sa na kod %s%s", self.pending,
                 f" (necakalo sa na {len(cakaju)} vypoctov)" if cakaju else "")
        self.quit()
        return True

    def _cakalo_sa_dost(self) -> bool:
        if not self.max_wait or self.pending_since is None:
            return False
        return self.clock() - self.pending_since >= self.max_wait

    def public(self) -> dict[str, Any]:
        return {"version": self.start_version, "pending": self.pending,
                "waiting_for": len(self.busy()) if self.pending else 0,
                "interval_seconds": self.interval, "branch": self.branch,
                "last_error": self.last_error}


def from_env(state: Any) -> "Updater | None":
    """Watcher podľa prostredia: `TRADEBOT_HUB_UPDATE` = minúty (0 alebo prázdne = vypnuté),
    `TRADEBOT_HUB_UPDATE_MAX_WAIT` = minúty čakania na dobehnutie (0 = koľko treba),
    `TRADEBOT_HUB_BRANCH` = vetva (default main)."""
    from tradebot.core.env import getenv

    try:
        minuty = float(getenv("HUB_UPDATE") or 0)
    except ValueError:
        return None
    if minuty <= 0:
        return None
    try:
        cakanie = float(getenv("HUB_UPDATE_MAX_WAIT") or 0)
    except ValueError:
        cakanie = 0.0
    return Updater(state, interval=minuty * 60, max_wait=cakanie * 60,
                   branch=(getenv("HUB_BRANCH") or "main").strip())
