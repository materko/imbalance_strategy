"""Nový kód na obchodnom stroji (docs/LIVE.md, fáza 2c) — `CodeUpdater`.

    upd = CodeUpdater(drivers, git=gitcode, reconciler=rec)      # v agentovi; `git` = modul s has_version/pull/version
    upd.installed()                                              # {"mt5": "<sha>"|None, "ninjatrader": ...} z markerov driverov
    result = upd.run({"version": "<sha>", "force": False, "requested_by": "rasto", "ts": 1.0})

Hub pošle v heartbeate `live.code_target`; agent ho v pomalom vlákne (nikdy v heartbeate) odovzdá sem.
Jedno `run`:

1. **Nič nerobiť, keď je hotovo**: každý driver už hlási `installed_version() == version` (a nie je `force`)
   → `ok` bez zásahu (po reštarte agenta uprostred aktualizácie sa tak nič nerobí dvakrát).
2. **Kód**: keď klon commit nemá (`git.has_version`), `git.pull()`; keď ho nemá ani potom, `error`
   (zadávateľ ho nepushol). Zmena HEAD = `code_changed` (agent sa potom reštartuje / hlási `needs_restart`).
3. **Brána** (`gate`): každé aktívne nasadenie tohto agenta musí byť `paused`/`flatten` a **bez pozície** —
   režim z posledného `control` v spoole (keď ho spool nemá, z toho, čo reconciler zapísal do control súboru),
   pozícia z fillov v spoole (`in` − `out` po id). Inštancia bez spoolu = pozícia neznáma = blokované.
   Dôvody idú do `reasons` a stav je `blocked`; `force` bránu preskočí.
4. **Platformy**: každý driver `install_code(version, účty platformy)` — chyba jedného drivera je `error`
   len preň, ostatné idú ďalej (`platforms`). Driver MT5 zavrie terminály (držia DLL) a nechá ich reštart
   na `ensure_instance` v ďalšom kole reconcilera; driver NT nakopíruje zdrojáky a preloží ich cez bežiaci NT.

Výsledok (`dict`) ide celý do heartbeatu ako `live.code_update`; hub `code_target` zmaže, keď je `ok`
pre tú istú verziu.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

from .drivers.base import Account, Driver
from .schema import CONTROL_MODES

__all__ = ["CodeUpdater", "position_from_spool", "gate_reasons", "SAFE_MODES"]

log = logging.getLogger(__name__)

#: Režimy, v ktorých stratégia nové vstupy neposiela — len v nich sa smie meniť kód pod ňou.
SAFE_MODES = ("paused", "flatten")
_FILL_MARK = b'"k":"fill"'


def _short(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}" if not isinstance(exc, (ValueError, OSError, RuntimeError)) else str(exc)
    return text[:500]


def position_from_spool(roots: list[Path], instance: str) -> float | None:
    """Čistá pozícia inštancie z fillov v spoole: za každé id vstupy − výstupy (v množstve), spolu v absolútnej
    hodnote (smer nie je podstatný — nenulové = niečo je otvorené). Číta všetky súbory inštancie (len riadky
    s `fill`, ostatné sa preskočia bez parsovania). `None` = inštancia v spoole nie je (pozícia neznáma)."""
    files: list[Path] = []
    for root in roots:
        d = Path(root) / instance
        if d.is_dir():
            files.extend(sorted(p for p in d.glob("*.jsonl") if p.is_file()))
    if not files:
        return None
    net: dict[str, float] = {}
    for f in files:
        try:
            with open(f, "rb") as fh:
                for raw in fh:
                    if _FILL_MARK not in raw and b'"k": "fill"' not in raw:
                        continue
                    try:
                        ev = json.loads(raw)
                    except ValueError:
                        continue
                    if not isinstance(ev, dict) or ev.get("k") != "fill":
                        continue
                    q = float(ev.get("qty") or 0)
                    key = str(ev.get("id") or "")
                    net[key] = net.get(key, 0.0) + (q if ev.get("side") == "in" else -q)
        except OSError:
            continue
    return sum(abs(v) for v in net.values() if abs(v) > 1e-9)


def gate_reasons(deployments: list[dict[str, Any]], spool_state: list[dict[str, Any]], roots: list[Path],
                 applied: dict[str, Any] | None = None) -> list[str]:
    """Prečo sa kód meniť nesmie — prázdny zoznam = smie. `deployments` = posledný požadovaný stav z hubu,
    `spool_state` = `tradebot.live.spool.latest_state`, `applied` = čo reconciler naposledy zapísal."""
    reasons: list[str] = []
    by_inst = {s.get("instance"): s for s in spool_state if isinstance(s, dict)}
    for d in deployments:
        if not isinstance(d, dict) or not d.get("active", True):
            continue
        inst = str(d.get("instance") or d.get("id") or "?")
        label = f"{d.get('strategy')} {d.get('symbol')} {d.get('tf')}m ({inst})"
        st = by_inst.get(inst)
        mode = (st or {}).get("mode")
        if mode is None:
            mode = ((applied or {}).get(d.get("id")) or {}).get("mode") or d.get("mode")
        if mode not in SAFE_MODES:
            reasons.append(f"{label}: obchoduje (režim {mode or '?'}) — najprv pauza alebo flatten")
        pos = position_from_spool(roots, inst)
        if pos is None:
            reasons.append(f"{label}: nemá spool, pozícia je neznáma")
        elif pos > 0:
            reasons.append(f"{label}: otvorená pozícia ({pos:g}) — najprv flatten")
    return reasons


class CodeUpdater:
    def __init__(self, drivers: dict[str, Driver], *, git: Any = None, reconciler: Any = None,
                 roots: Callable[[], list[Path]] | None = None, clock: Callable[[], float] = time.time,
                 by: str = "hub") -> None:
        self.drivers: dict[str, Driver] = dict(drivers)
        self.git = git
        self.reconciler = reconciler
        self._roots = roots
        self.clock = clock
        self.by = by
        self.last: dict[str, Any] | None = None

    # -- čo je na stroji ------------------------------------------------------- #

    def roots(self) -> list[Path]:
        if self._roots is not None:
            return list(self._roots())
        from .spool import default_roots

        return default_roots()

    def installed(self) -> dict[str, str | None]:
        """Marker každého drivera; driver, ktorý pri čítaní padne, je `None`."""
        out: dict[str, str | None] = {}
        for key, drv in self.drivers.items():
            try:
                out[key] = drv.installed_version()
            except Exception as exc:  # noqa: BLE001 - stav nesmie zhodiť heartbeat
                log.debug("code update: installed_version %s: %s", key, exc)
                out[key] = None
        return out

    def _desired(self) -> dict[str, Any]:
        state = getattr(self.reconciler, "state", None) or {}
        return dict(state.get("desired") or {})

    def _accounts(self, platform: str) -> list[Account]:
        out = []
        for raw in self._desired().get("accounts") or []:
            if isinstance(raw, dict) and str(raw.get("platform") or "") == platform:
                out.append(Account.from_dict(raw))
        return out

    def gate(self) -> list[str]:
        """Dôvody, prečo sa kód meniť nesmie (`gate_reasons` nad posledným stavom z hubu a spoolom)."""
        from .spool import latest_state

        desired = self._desired()
        roots = self.roots()
        applied = dict((getattr(self.reconciler, "state", None) or {}).get("applied") or {})
        return gate_reasons(list(desired.get("deployments") or []), latest_state(roots), roots, applied)

    # -- jedna aktualizácia ---------------------------------------------------- #

    def run(self, target: dict[str, Any]) -> dict[str, Any]:
        """Jedna aktualizácia podľa `code_target` hubu. Nikdy nevyhodí výnimku; výsledok je aj v `self.last`."""
        version = str((target or {}).get("version") or "")
        force = bool((target or {}).get("force"))
        out: dict[str, Any] = {"version": version, "force": force, "status": "ok", "error": None, "reasons": [],
                               "pulled": False, "code_changed": False, "platforms": {}, "ts": self.clock(),
                               "requested_by": (target or {}).get("requested_by"), "target_ts": (target or {}).get("ts")}
        try:
            self._run(out, version, force)
        except Exception as exc:  # noqa: BLE001 - aktualizácia nesmie zhodiť pomalé vlákno agenta
            out["status"], out["error"] = "error", _short(exc)
            log.exception("code update: %s", out["error"])
        out["installed"] = self.installed()
        self.last = out
        return out

    def _run(self, out: dict[str, Any], version: str, force: bool) -> None:
        if not version:
            out["status"], out["error"] = "error", "code_target bez verzie"
            return
        if not self.drivers:
            out["status"], out["error"] = "error", "na tomto stroji nie je žiadna platforma (driver)"
            return
        installed = self.installed()
        if not force and all(_same(installed.get(k), version) for k in self.drivers):
            out["noop"] = True
            for k in self.drivers:
                out["platforms"][k] = {"status": "ok", "installed": installed.get(k), "noop": True}
            return
        # 1. kód
        if self.git is not None:
            before = self.git.version() or ""
            if not self.git.has_version(version):
                r = self.git.pull()
                out["pulled"] = True
                out["pull"] = (r or {}).get("output", "")[-300:] if isinstance(r, dict) else str(r)[-300:]
                if not self.git.has_version(version):
                    out["status"] = "error"
                    out["error"] = (f"klon nemá commit {version} ani po git pull (HEAD {self.git.version() or '?'}) "
                                    f"— zadávateľ ho musí pushnúť do main. {out['pull']}".strip())
                    return
            now = self.git.version() or ""
            out["code_changed"] = bool(before and now and before != now)
        # 2. brána
        if not force:
            reasons = self.gate()
            if reasons:
                out["status"], out["reasons"] = "blocked", reasons
                out["error"] = "blokované: " + "; ".join(reasons)[:800]
                return
        # 3. platformy
        for key, drv in self.drivers.items():
            entry: dict[str, Any] = {"status": "ok", "error": None}
            try:
                info = drv.install_code(version, self._accounts(key))
                if isinstance(info, dict):
                    entry.update({k: v for k, v in info.items() if k not in ("status", "error")})
                entry["installed"] = drv.installed_version()
                log.info("code update: %s -> %s", key, version)
            except Exception as exc:  # noqa: BLE001 - chyba jednej platformy neblokuje druhú
                entry["status"], entry["error"] = "error", _short(exc)
                try:
                    entry["installed"] = drv.installed_version()
                except Exception:  # noqa: BLE001
                    entry["installed"] = None
                log.warning("code update: %s zlyhalo: %s", key, entry["error"])
            out["platforms"][key] = entry
        chyby = [f"{k}: {v['error']}" for k, v in out["platforms"].items() if v.get("status") == "error"]
        if chyby:
            out["status"], out["error"] = "error", "; ".join(chyby)[:800]


def _same(installed: str | None, wanted: str) -> bool:
    """Krátky aj dlhý sha toho istého commitu sú to isté."""
    if not installed or not wanted:
        return False
    a, b = installed.strip().lower(), wanted.strip().lower()
    return a == b or (len(a) >= 7 and len(b) >= 7 and (a.startswith(b) or b.startswith(a)))
