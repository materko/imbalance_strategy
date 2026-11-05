"""Pluginy agenta (docs/HUB.md, „Pluginy agenta“): vlastný kód, ktorý beží v procese agenta (headless aj webapp).

Plugin = balík `tester/hub/agent_plugins/<meno>/`, ktorý vystaví `PLUGIN = <podtrieda AgentPlugin>` — dnes
`telegram` (správy zo spoolu, príkazy, 📈 Výkon). `AgentPluginHost` ich nájde sám, každému dá
`AgentPluginContext` a vlastné vlákno; agent nepozná plugin menom.

**Nový kód pluginu bez reštartu** (`PluginUpdater`, volá ho pomalé vlákno agenta):

1. kód na disku je novší než načítaný a zmena je len v adresároch pluginov (+ neutrálne súbory —
   `tester.hub.pluginreload`) → zmenené pluginy sa načítajú znova (`reload`),
2. na obchodnom stroji (`role: live`) každých `interval` sekúnd `git fetch`; keď `origin/main` prináša len
   zmeny pluginov, agent si ich sám pullne (bez brány nasadení — kód platforiem sa nemení) a načíta podľa 1.

Zmena rozhrania (`base.py`, tento súbor, čokoľvek mimo adresárov pluginov) ide po starom: pull cez nasadenie
kódu / pokyn hubu a reštart agenta.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
import subprocess
import threading
import time
import traceback
from typing import Any, Callable

from tradebot.core.paths import REPO

from ..pluginreload import AGENT_PLUGINS, changed_files, plugin_only, reload_package
from .base import API, AgentPlugin, AgentPluginContext

__all__ = ["AgentPlugin", "AgentPluginContext", "AgentPluginHost", "PluginUpdater", "discover", "API"]

log = logging.getLogger(__name__)

#: Koľko sekúnd sa pri reloade čaká, kým starý plugin dokončí tick.
RELOAD_JOIN_SECONDS = 60.0
#: Pauza po výnimke v ticku.
ERROR_WAIT_SECONDS = 5.0


def discover() -> list[str]:
    """Mená balíkov v `tester/hub/agent_plugins/` (bez `_…`), v abecednom poradí."""
    return sorted(m.name for m in pkgutil.iter_modules(__path__) if m.ispkg and not m.name.startswith("_"))


def _load_class(name: str, fresh: bool = False) -> type[AgentPlugin]:
    full = f"{__name__}.{name}"
    mod = reload_package(full) if fresh else importlib.import_module(full)
    cls = getattr(mod, "PLUGIN", None)
    if not (isinstance(cls, type) and issubclass(cls, AgentPlugin)):
        raise TypeError(f"{name}: balík nevystavuje PLUGIN = podtrieda AgentPlugin")
    return cls


class _Slot:
    def __init__(self, name: str) -> None:
        self.name = name
        self.plugin: AgentPlugin | None = None
        self.ctx: AgentPluginContext | None = None
        self.load_error = ""
        self.last_error = ""
        self.thread: threading.Thread | None = None
        self.stop = threading.Event()
        self.reloads = 0
        self.loaded_at = 0.0


class AgentPluginHost:
    def __init__(self, context: Callable[[str, threading.Event], AgentPluginContext], *,
                 names: list[str] | None = None, classes: dict[str, type[AgentPlugin]] | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        """`context(meno, stopping)` vyrobí kontext pluginu; `classes` podstrčí pluginy (testy)."""
        self.context = context
        self.clock = clock
        self._classes = classes
        self._stop = threading.Event()
        self._started = False
        self._lock = threading.Lock()
        self.slots: dict[str, _Slot] = {}
        for name in (sorted(classes) if classes is not None else (names if names is not None else discover())):
            self.slots[name] = self._load(name)

    def _load(self, name: str, fresh: bool = False) -> _Slot:
        slot = _Slot(name)
        slot.loaded_at = self.clock()
        try:
            cls = self._classes[name] if self._classes is not None else _load_class(name, fresh)
            p = cls()
            p.name = name
            p.title = p.title or name
            ctx = self.context(name, slot.stop)
            p.setup(ctx)
            slot.plugin, slot.ctx = p, ctx
        except Exception as exc:  # noqa: BLE001 - zlý plugin nesmie zhodiť agenta
            slot.load_error = f"{type(exc).__name__}: {exc}"
            log.warning("plugin agenta %s sa nenačítal: %s", name, slot.load_error)
        return slot

    # -- vlákna -------------------------------------------------------------- #

    def start(self) -> None:
        self._started = True
        for s in list(self.slots.values()):
            self._start_slot(s)

    def _start_slot(self, s: _Slot) -> None:
        if s.plugin is None or self._stop.is_set():
            return
        plugin = s.plugin

        def loop() -> None:
            while not (self._stop.is_set() or s.stop.is_set()):
                try:
                    plugin.tick()
                    s.last_error = ""
                except Exception as exc:  # noqa: BLE001 - vlákno nesmie umrieť
                    if s.last_error != f"{type(exc).__name__}: {exc}":
                        log.warning("plugin agenta %s: %s: %s\n%s", s.name, type(exc).__name__, exc,
                                    traceback.format_exc(limit=4))
                    s.last_error = f"{type(exc).__name__}: {exc}"
                    if s.stop.wait(ERROR_WAIT_SECONDS):
                        break
                    continue
                if plugin.interval > 0 and s.stop.wait(float(plugin.interval)):
                    break

        s.thread = threading.Thread(target=loop, name=f"hub-agent-plugin-{s.name}", daemon=True)
        s.thread.start()

    def stop(self) -> None:
        self._stop.set()
        for s in list(self.slots.values()):
            s.stop.set()
        for s in list(self.slots.values()):
            if s.thread is not None and s.thread.is_alive():
                s.thread.join(timeout=10)
            if s.plugin is not None:
                try:
                    s.plugin.teardown()
                except Exception as exc:  # noqa: BLE001
                    log.warning("plugin agenta %s teardown: %s", s.name, exc)

    def reload(self, names: set[str] | list[str], *, join_seconds: float = RELOAD_JOIN_SECONDS) -> bool:
        """Načíta pluginy `names` znova z disku (zastaví vlákno, `teardown`, nový import, `setup`, nové vlákno);
        nový na disku pribudne, zmiznutý sa odoberie. `False` = starý plugin nedobehol do `join_seconds`."""
        with self._lock:
            na_disku = set(discover()) if self._classes is None else set(self._classes)
            for name in sorted(set(names)):
                stary = self.slots.get(name)
                if stary is not None:
                    stary.stop.set()
                    if stary.thread is not None and stary.thread.is_alive():
                        stary.thread.join(timeout=join_seconds)
                        if stary.thread.is_alive():
                            log.warning("plugin agenta %s nedobehol do %.0f s — reload sa vzdáva", name, join_seconds)
                            return False
                    if stary.plugin is not None:
                        try:
                            stary.plugin.teardown()
                        except Exception as exc:  # noqa: BLE001
                            log.warning("plugin agenta %s teardown: %s", name, exc)
                if name not in na_disku:
                    self.slots.pop(name, None)
                    log.info("plugin agenta %s z disku zmizol — odobratý", name)
                    continue
                novy = self._load(name, fresh=True)
                novy.reloads = (stary.reloads + 1) if stary is not None else 0
                self.slots = dict(sorted({**self.slots, name: novy}.items()))
                if self._started:
                    self._start_slot(novy)
                log.info("plugin agenta %s načítaný znova%s", name,
                         f" — CHYBA {novy.load_error}" if novy.load_error else "")
            return True

    # -- čo agent od pluginov chce ----------------------------------------- #

    def _each(self) -> list[tuple[str, AgentPlugin]]:
        return [(n, s.plugin) for n, s in list(self.slots.items()) if s.plugin is not None]

    def status(self) -> dict[str, Any]:
        """`meno → stav` pre heartbeat a webapp: stav pluginu + `load_error`, `last_error`, `reloads`."""
        out: dict[str, Any] = {}
        for name, s in list(self.slots.items()):
            detail: Any = None
            if s.plugin is not None:
                try:
                    detail = s.plugin.status()
                except Exception as exc:  # noqa: BLE001
                    detail = {"error": f"{type(exc).__name__}: {exc}"}
            out[name] = {"title": s.plugin.title if s.plugin else name, "status": detail,
                         "running": bool(s.thread and s.thread.is_alive()), "load_error": s.load_error,
                         "last_error": s.last_error, "reloads": s.reloads, "loaded_at": s.loaded_at, "api": API}
        return out

    def brief(self) -> dict[str, dict[str, Any]]:
        """`meno → {title, running, active, error}` pre heartbeat a kartu Hub (`active` = stroj plugin používa —
        `AgentPlugin.active`; nenačítaný plugin sa počíta ako používaný, aby jeho chyba bola vidno)."""
        out: dict[str, dict[str, Any]] = {}
        for name, s in list(self.slots.items()):
            aktivny = True
            if s.plugin is not None:
                try:
                    aktivny = bool(s.plugin.active())
                except Exception:  # noqa: BLE001
                    aktivny = True
            out[name] = {"title": s.plugin.title if s.plugin else name, "running": bool(s.thread and s.thread.is_alive()),
                         "active": aktivny, "error": str(s.load_error or s.last_error or "")[:300]}
        return out

    def overrides(self) -> list[dict[str, Any]]:
        """Lokálne prepnuté režimy všetkých pluginov (`plugin` = kto ho drží)."""
        out = []
        for name, p in self._each():
            try:
                out += [{**o, "plugin": name} for o in p.overrides() or []]
            except Exception as exc:  # noqa: BLE001
                log.debug("plugin agenta %s overrides: %s", name, exc)
        return out

    def drop_override(self, plugin: str, instance: str) -> None:
        s = self.slots.get(plugin)
        if s is not None and s.plugin is not None:
            try:
                s.plugin.drop_override(instance)
            except Exception as exc:  # noqa: BLE001
                log.debug("plugin agenta %s drop_override: %s", plugin, exc)

    def desired(self, desired: dict[str, Any], now: float) -> None:
        for name, p in self._each():
            try:
                p.desired(desired, now)
            except Exception as exc:  # noqa: BLE001
                log.debug("plugin agenta %s desired: %s", name, exc)


def _fetch(branch: str) -> bool:
    try:
        r = subprocess.run(["git", "fetch", "--quiet", "origin", branch], cwd=str(REPO), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


class PluginUpdater:
    """Drží pluginy agenta na najnovšom kóde bez reštartu (viď docstring modulu). `tick()` volá pomalé vlákno
    agenta; vráti verziu, na ktorú sa pluginy práve načítali (agent si ju vezme ako svoju), inak `None`."""

    def __init__(self, host: AgentPluginHost, loaded: str, *, version: Callable[[], str],
                 can_pull: Callable[[], bool] = lambda: False, pull: Callable[[], dict[str, Any]] | None = None,
                 fetch: Callable[[str], bool] = _fetch, changed: Callable[..., list[str] | None] = changed_files,
                 dirty: Callable[[], list[str]] = lambda: [], branch: str = "main", interval: float = 300.0,
                 clock: Callable[[], float] = time.time) -> None:
        self.host = host
        #: commit, z ktorého sú načítané pluginy aj zvyšok procesu
        self.loaded = loaded
        self.version = version
        self.can_pull = can_pull
        self.pull = pull
        self.fetch = fetch
        self.changed = changed
        self.dirty = dirty
        self.branch = branch
        self.interval = float(interval)
        self.clock = clock
        self._fetched_at: float | None = None
        #: (načítaný, na disku), pri ktorých reload nejde — nepočítať diff znova každé kolo
        self._rejected: tuple[str, str] | None = None
        self.last: dict[str, Any] | None = None

    def tick(self) -> str | None:
        nova = self._from_disk()
        if nova is not None or self.interval <= 0 or not self.can_pull():
            return nova
        now = self.clock()
        if self._fetched_at is not None and now - self._fetched_at < self.interval:
            return None
        self._fetched_at = now
        if self.pull is None or not self.fetch(self.branch):
            return None
        zmeny = self.changed("HEAD", f"origin/{self.branch}", remote_side=True)
        mena = plugin_only(zmeny, AGENT_PLUGINS)
        if not zmeny or not mena or self.dirty():
            return None
        log.info("plugin agenta: origin/%s mení len pluginy %s — ťahám kód", self.branch, ", ".join(sorted(mena)))
        r = self.pull()
        if not r.get("ok"):
            self.last = {"status": "error", "error": str(r.get("output") or "")[-300:], "at": now}
            log.warning("plugin agenta: pull zlyhal: %s", self.last["error"])
            return None
        return self._from_disk()

    def _from_disk(self) -> str | None:
        """Kód na disku je novší než načítaný a mení len pluginy → reload; vráti novú verziu."""
        disk = self.version()
        if not disk or not self.loaded or disk == self.loaded or self._rejected == (self.loaded, disk):
            return None
        mena = plugin_only(self.changed(self.loaded, disk), AGENT_PLUGINS)
        if mena is None:
            self._rejected = (self.loaded, disk)
            return None   # zmenilo sa rozhranie / iný kód — agent sa reštartuje po starom
        if mena and not self.host.reload(mena):
            return None
        stary, self.loaded = self.loaded, disk
        self.last = {"status": "ok", "version": disk, "plugins": sorted(mena), "at": self.clock()}
        log.info("plugin agenta: kód %s -> %s, načítané znova: %s", stary, disk, ", ".join(sorted(mena)) or "nič")
        return disk
