"""Zosúladenie požadovaného stavu z hubu so strojom (docs/LIVE.md, fáza 2b) — `Reconciler`.

    rec = Reconciler(load_drivers(), LIVE_APPLY_STATE)
    rec.run(heartbeat_response["live"])     # v pomalom vlákne agenta, nikdy v heartbeate
    rec.fragment()                          # {"applied": [...], "secret_ack": [...]} do ďalšieho heartbeatu

Hub posiela **celý** zoznam účtov a nasadení tohto agenta pri každom heartbeate; reconciler pre každý
účet nájde driver platformy a v tomto poradí: heslo → `store_secret` (a ack), aktívne nasadenie →
`ensure_profile` + `write_control`, neaktívne alebo z hubu zmiznuté → `remove_instance`, potom za účet
`ensure_instance` s aktívnymi nasadeniami, ktoré prešli. Výsledok je `status` `ok`/`error` (+ text
chyby) ku každému nasadeniu.

Pravidlá:

- **Nič nevyhodí von.** Chyba drivera je `status: error` k tomu jednému nasadeniu (alebo účtu) a ostatné
  idú ďalej; hub bez `live` (starý hub) = nič sa nerobí.
- **Idempotentné.** Nasadenie, ktoré sa od posledného úspešného kola nezmenilo (config, režim, profil,
  účet), sa na disk znova nepíše — adaptéry čítajú control podľa mtime a každý zápis by bol nová
  správa. `ensure_instance` sa volá každé kolo (driver tak spozná spadnutý terminál), sám nesmie nič
  reštartovať, keď stav sedí.
- **Prežije reštart.** Posledný požadovaný stav (bez hesiel) a čo sa z neho aplikovalo, je v
  `tester/live/apply_state.json`; po štarte agent hlási to isté, kým hub nepošle nový stav, a nasadenie,
  ktoré medzitým z hubu zmizlo, vie odstrániť.
- **Bez sirôt.** Ku každému nasadeniu si stav pamätá `instance` a cestu naposledy zapísaného control
  súboru (`control`); keď sa id inštancie zmení (iný login/server účtu), starý control ide cez
  `remove_instance` drivera (pauza → zmazanie až po zastavení), nie ostane ležať ako správa pre EA.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.core.paths import LIVE_APPLY_STATE

from .drivers.base import Account, Deployment, Driver

__all__ = ["Reconciler", "config_hash"]

log = logging.getLogger(__name__)

#: Polia účtu, ktoré sa nikdy neukladajú (heslo nesie hub len do prevzatia).
_SECRET_FIELDS = ("secret", "password")
#: Polia `applied` len pre tento stroj — do heartbeatu nejdú (podpis, id inštancie, cesta control súboru).
_LOCAL_FIELDS = ("sig", "instance", "control")


def config_hash(config: dict[str, Any]) -> str:
    """sha256 kanonického JSON configu — to isté, čo počíta hub (`config_hash` nasadenia)."""
    text = json.dumps(config or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scrub(account: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in account.items() if k not in _SECRET_FIELDS}


def _short(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}" if not isinstance(exc, (ValueError, OSError)) else str(exc)
    return text[:500]


class Reconciler:
    def __init__(self, drivers: dict[str, Driver], state_path: Path | None = None, *,
                 by: str = "hub", clock=time.time) -> None:
        self.drivers: dict[str, Driver] = dict(drivers)
        self.state_path = Path(state_path or LIVE_APPLY_STATE)
        self.by = by
        self.clock = clock
        self._lock = threading.RLock()
        self.state: dict[str, Any] = self._load()
        self.last_run: float | None = None
        self.last_error: str | None = None
        #: Chyby, ktoré sa už logovali — tá istá chyba každých 10 s do logu nepatrí.
        self._logged: dict[str, str] = {}

    # -- stav na disku ------------------------------------------------------- #

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("desired", {})
        data.setdefault("applied", {})
        data.setdefault("accounts", {})
        data.setdefault("secret_ack", [])
        return data

    def _save(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
            os.replace(tmp, self.state_path)
        except OSError as exc:
            log.warning("live apply: stav sa nepodarilo zapísať do %s: %s", self.state_path, exc)

    # -- pre heartbeat ------------------------------------------------------- #

    def fragment(self) -> dict[str, Any]:
        """`applied` + `secret_ack` do heartbeatu — z posledného kola, po reštarte z disku."""
        with self._lock:
            applied = [{k: v for k, v in e.items() if k not in _LOCAL_FIELDS} for e in self.state["applied"].values()]
            return {"applied": applied, "secret_ack": list(self.state.get("secret_ack") or [])}

    def status(self) -> dict[str, Any]:
        """Stav pre webapp/CLI: drivery, posledné kolo, nasadenia a čo o účtoch vie driver."""
        with self._lock:
            accounts: dict[str, Any] = {}
            for raw in (self.state["desired"].get("accounts") or []):
                acc = Account.from_dict(raw)
                info: dict[str, Any] = dict(self.state["accounts"].get(acc.id) or {})
                drv = self.drivers.get(acc.platform)
                if drv is not None:
                    try:
                        info["driver"] = drv.status(acc)
                    except Exception as exc:  # noqa: BLE001 - stav nesmie zhodiť API
                        info["driver"] = {"error": _short(exc)}
                accounts[acc.id] = info
            return {
                "drivers": sorted(self.drivers), "state_path": str(self.state_path),
                "last_run": datetime.fromtimestamp(self.last_run, tz=timezone.utc).isoformat(timespec="seconds")
                if self.last_run else None,
                "last_error": self.last_error, "updated": self.state.get("updated"),
                "deployments": self.fragment()["applied"], "accounts": accounts,
            }

    # -- jedno kolo ---------------------------------------------------------- #

    @staticmethod
    def _signature(acc: Account, dep: Deployment) -> str:
        return config_hash({"cfg": config_hash(dep.config), "mode": dep.mode, "profile": dep.profile,
                            "strategy": dep.strategy, "symbol": dep.symbol, "tf": dep.tf,
                            "login": acc.login, "server": acc.server, "terminal": acc.terminal,
                            "portable": acc.portable, "instance": dep.instance})

    def _warn_once(self, key: str, text: str) -> None:
        if self._logged.get(key) != text:
            self._logged[key] = text
            log.warning("live apply: %s: %s", key, text)

    def run(self, desired: dict[str, Any] | None) -> dict[str, Any]:
        """Jedno kolo nad požadovaným stavom hubu (`live` z odpovede heartbeatu). Vráti `fragment()`."""
        if not isinstance(desired, dict):
            return self.fragment()   # starý hub bez `live` — nič sa nemení
        try:
            with self._lock:
                self._run(desired)
                self.last_error = None
        except Exception as exc:  # noqa: BLE001 - kolo nesmie zhodiť pomalé vlákno agenta
            self.last_error = _short(exc)
            log.exception("live apply: kolo zlyhalo: %s", self.last_error)
        finally:
            self.last_run = self.clock()
        return self.fragment()

    def _run(self, desired: dict[str, Any]) -> None:
        accounts = {a.id: a for a in (Account.from_dict(d) for d in desired.get("accounts") or [] if isinstance(d, dict)) if a.id}
        deployments = [Deployment.from_dict(d) for d in desired.get("deployments") or [] if isinstance(d, dict)]
        deployments = [d for d in deployments if d.id]
        prev_applied: dict[str, Any] = dict(self.state.get("applied") or {})
        prev_desired: dict[str, Any] = self.state.get("desired") or {}
        prev_accounts = {a.get("id"): Account.from_dict(a) for a in prev_desired.get("accounts") or [] if isinstance(a, dict)}
        current_ids = {d.id for d in deployments}
        # zmizlo z hubu (zmazané) — odstrániť; čo už bolo neaktívne, je odstránené z minula
        vanished = [Deployment.from_dict(d) for d in prev_desired.get("deployments") or []
                    if isinstance(d, dict) and d.get("id") and d["id"] not in current_ids and d.get("active", True)]

        applied: dict[str, dict[str, Any]] = {}
        account_status: dict[str, dict[str, Any]] = {}
        secret_ack: list[str] = []

        # 1. heslá — raz na účet, ack len po úspešnom uložení
        for acc in accounts.values():
            drv = self.drivers.get(acc.platform)
            if drv is None:
                account_status[acc.id] = {"error": f"driver pre platformu {acc.platform!r} nie je na tomto stroji"}
                self._warn_once(f"účet {acc.id}", account_status[acc.id]["error"])
                continue
            account_status[acc.id] = {}
            if acc.secret:
                try:
                    drv.store_secret(acc, acc.secret)
                    secret_ack.append(acc.id)
                    log.info("live apply: heslo účtu %s prevzaté", acc.id)
                except Exception as exc:  # noqa: BLE001
                    account_status[acc.id]["error"] = f"heslo sa nepodarilo uložiť: {_short(exc)}"
                    self._warn_once(f"heslo {acc.id}", account_status[acc.id]["error"])

        # 2. nasadenia po účtoch (aj účty, ktorým z hubu zmizlo nasadenie — graf treba odobrať)
        by_account: dict[str, list[Deployment]] = {}
        for dep in deployments:
            by_account.setdefault(dep.account, []).append(dep)
        vanished_by: dict[str, list[Deployment]] = {}
        for dep in vanished:
            vanished_by.setdefault(dep.account, []).append(dep)

        for acc_id in sorted(set(by_account) | set(vanished_by)):
            acc = accounts.get(acc_id) or prev_accounts.get(acc_id)
            deps = by_account.get(acc_id, [])
            drv = self.drivers.get(acc.platform) if acc is not None else None
            if acc is None or drv is None:
                chyba = (f"účet {acc_id!r} nie je v zozname účtov" if acc is None
                         else f"driver pre platformu {acc.platform!r} nie je na tomto stroji")
                for dep in deps:
                    applied[dep.id] = self._entry(dep, "error", chyba)
                continue
            active_ok: list[Deployment] = []
            touched = False
            for dep in deps:
                entry = self._entry(dep, "ok", "")
                predtym = prev_applied.get(dep.id) or {}
                try:
                    dep.instance = drv.instance_of(acc, dep)
                    entry["instance"] = dep.instance
                    if not dep.active:
                        self._retire_old_instance(drv, acc, dep, predtym)
                        drv.remove_instance(acc, dep)
                        touched = True
                        applied[dep.id] = entry
                        continue
                    dep.validate()
                    sig = self._signature(acc, dep)
                    entry["sig"] = sig
                    if predtym.get("sig") == sig and predtym.get("status") == "ok" and predtym.get("active", True):
                        entry["unchanged"] = True
                        if predtym.get("control"):
                            entry["control"] = predtym["control"]
                    else:
                        self._retire_old_instance(drv, acc, dep, predtym)
                        drv.ensure_profile(dep)
                        entry["control"] = str(drv.write_control(dep))
                        touched = True
                        log.info("live apply: nasadenie %s (%s %s %dm, %s, %s) zapísané", dep.id, dep.strategy,
                                 dep.symbol, dep.tf, dep.profile, dep.mode)
                    active_ok.append(dep)
                except Exception as exc:  # noqa: BLE001 - chyba jedného nasadenia
                    entry["status"], entry["error"] = "error", _short(exc)
                    entry.pop("sig", None)
                    self._warn_once(f"nasadenie {dep.id}", entry["error"])
                applied[dep.id] = entry
            for dep in vanished_by.get(acc_id, []):
                try:
                    drv.remove_instance(acc, dep)
                    touched = True
                    log.info("live apply: nasadenie %s z hubu zmizlo — odstránené", dep.id)
                except Exception as exc:  # noqa: BLE001
                    self._warn_once(f"odstránenie {dep.id}", _short(exc))
            try:
                drv.ensure_instance(acc, active_ok)
            except Exception as exc:  # noqa: BLE001 - inštancia účtu: chyba ku všetkým jeho aktívnym nasadeniam
                chyba = f"inštancia: {_short(exc)}"
                self._warn_once(f"inštancia {acc_id}", chyba)
                for dep in active_ok:
                    applied[dep.id].update(status="error", error=chyba)
                    applied[dep.id].pop("sig", None)
            if touched:
                self._logged.pop(f"inštancia {acc_id}", None)

        self.state["desired"] = {"accounts": [_scrub(a) for a in desired.get("accounts") or [] if isinstance(a, dict)],
                                 "deployments": [d for d in desired.get("deployments") or [] if isinstance(d, dict)]}
        self.state["applied"] = applied
        self.state["accounts"] = account_status
        self.state["secret_ack"] = secret_ack
        self.state["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._save()

    @staticmethod
    def _entry(dep: Deployment, status: str, error: str) -> dict[str, Any]:
        return {"deployment": dep.id, "config_hash": dep.config_hash or config_hash(dep.config),
                "mode": dep.mode, "active": dep.active, "status": status, "error": error}

    @staticmethod
    def _retire_old_instance(drv: Driver, acc: Account, dep: Deployment, predtym: dict[str, Any]) -> None:
        """Nasadenie malo minule iné id inštancie (zmenil sa login/server účtu): jeho starý control súbor
        by ostal ako sirota — driver ho odstráni tak, ako rušené nasadenie (pauza, zmazanie po zastavení)."""
        old = str(predtym.get("instance") or "")
        if not old or old == dep.instance:
            return
        log.info("live apply: nasadenie %s zmenilo inštanciu %s -> %s, stará sa odstraňuje", dep.id, old, dep.instance)
        drv.remove_instance(acc, dataclasses.replace(dep, instance=old))
