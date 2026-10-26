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
- **Nenabehla.** Aplikované nasadenie (`ok`), ktorého inštancia na platforme nenabehla (driver to vie z
  logov platformy, `instance_issue`), ostáva `ok`, ale `error` nesie `nenabehla: <dôvod>` — prejde aj cez
  starší hub a webapp to ukáže ako upozornenie. Zisťuje sa každé kolo a bez nového stavu z hubu cez
  `refresh()` (najviac raz za `ISSUE_REFRESH_SECONDS`).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.core.paths import LIVE_APPLY_STATE

from .drivers.base import Account, Deployment, Driver
from .routes import EXECUTOR_KIND

__all__ = ["Reconciler", "config_hash", "ISSUE_PREFIX"]

log = logging.getLogger(__name__)

#: Polia účtu, ktoré sa nikdy neukladajú (heslo nesie hub len do prevzatia).
_SECRET_FIELDS = ("secret", "password")
#: Polia `applied` len pre tento stroj — do heartbeatu nejdú (podpis, id inštancie, cesta control súboru).
_LOCAL_FIELDS = ("sig", "instance", "control")
#: Začiatok `error` pri stave `ok`: nasadenie je aplikované, ale inštancia na platforme nenabehla.
ISSUE_PREFIX = "nenabehla: "
#: Ako často `refresh()` (bez nového stavu z hubu) znova pozrie, či inštancie nabehli.
ISSUE_REFRESH_SECONDS = 15.0


def config_hash(config: dict[str, Any]) -> str:
    """sha256 kanonického JSON configu — to isté, čo počíta hub (`config_hash` nasadenia)."""
    text = json.dumps(config or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scrub(account: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in account.items() if k not in _SECRET_FIELDS}


def _short(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}" if not isinstance(exc, (ValueError, OSError)) else str(exc)
    return text[:500]


def _spool_position(instance: str) -> float | None:
    """Otvorené množstvo inštancie zo spoolu tohto stroja (`update.position_from_spool`), None = nevedno."""
    from .spool import default_roots
    from .update import position_from_spool

    return position_from_spool(default_roots(), instance)


class Reconciler:
    def __init__(self, drivers: dict[str, Driver], state_path: Path | None = None, *,
                 by: str = "hub", clock=time.time, position=None) -> None:
        self.drivers: dict[str, Driver] = dict(drivers)
        #: `instance -> otvorené množstvo | None` — rušené nasadenie s otvorenou pozíciou sa neodoberie
        #: (audit N-LIVE-15); predvolene zo spoolu stroja ako brána aktualizácie kódu
        self.position = position or _spool_position
        self.state_path = Path(state_path or LIVE_APPLY_STATE)
        self.by = by
        self.clock = clock
        self._lock = threading.RLock()
        self.state: dict[str, Any] = self._load()
        self.last_run: float | None = None
        self.last_error: str | None = None
        #: Chyby, ktoré sa už logovali — tá istá chyba každých 10 s do logu nepatrí.
        self._logged: dict[str, str] = {}
        self._issues_checked: float | None = None

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
        """`applied` + `secret_ack` do heartbeatu — z posledného kola, po reštarte z disku — a `exec_symbols`:
        symboly MT5 účtov z čerstvého heartbeatu ich exekútorov na tomto stroji (hub podľa nich odmietne route
        na symbol, ktorý účet nemá)."""
        with self._lock:
            applied = [{k: v for k, v in e.items() if k not in _LOCAL_FIELDS} for e in self.state["applied"].values()]
            return {"applied": applied, "secret_ack": list(self.state.get("secret_ack") or []),
                    "exec_symbols": self.exec_symbols()}

    def exec_symbols(self) -> dict[str, list[str]]:
        """`{MT5 účet: [symbol, …]}` z `exec/<id>.hb.json` exekútorov z požadovaného stavu (`kind: executor`);
        účet bez súboru alebo so starým heartbeatom (`EXEC_HB_MAX_AGE`) chýba. Nikdy nevyhodí výnimku."""
        from .routes import executor_symbols

        out: dict[str, list[str]] = {}
        try:
            deps = (self.state.get("desired") or {}).get("deployments") or []
            for d in deps:
                if not isinstance(d, dict) or d.get("kind") != EXECUTOR_KIND or not d.get("instance") or not d.get("account"):
                    continue
                names = executor_symbols(str(d["instance"]), now=self.clock())
                if names:
                    out[str(d["account"])] = names
        except Exception as exc:  # noqa: BLE001 - heartbeat musí odísť
            log.debug("live apply: symboly exekútorov sa nedali zistiť: %s", exc)
        return out

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
        sig = {"cfg": config_hash(dep.config), "mode": dep.mode, "profile": dep.profile,
               "strategy": dep.strategy, "symbol": dep.symbol, "tf": dep.tf,
               "login": acc.login, "server": acc.server, "terminal": acc.terminal,
               "portable": acc.portable, "instance": dep.instance}
        if dep.slot or dep.own_terminal:   # bez nich podpis ako doteraz — nič sa zbytočne neprepisuje
            sig.update(slot=dep.slot, own_terminal=dep.own_terminal)
        if acc.rev:   # bez `rev` (starý hub) ostáva podpis ako doteraz — nič sa zbytočne neprepisuje
            sig["rev"] = acc.rev
        return config_hash(sig)

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

    def refresh(self) -> dict[str, Any]:
        """Bez nového stavu z hubu: len znova zistí, či inštancie aplikovaných nasadení nabehli (najviac raz
        za `ISSUE_REFRESH_SECONDS`), a zmenu uloží. Vráti `fragment()`."""
        try:
            with self._lock:
                if self._issues_checked is None or self.clock() - self._issues_checked >= ISSUE_REFRESH_SECONDS:
                    if self._check_issues():
                        self._save()
        except Exception as exc:  # noqa: BLE001 - nesmie zhodiť pomalé vlákno agenta
            log.warning("live apply: kontrola inštancií zlyhala: %s", _short(exc))
        return self.fragment()

    def _check_issues(self) -> bool:
        """Ku každému aplikovanému (`ok`) aktívnemu nasadeniu sa driver opýta, či jeho inštancia nenabehla;
        dôvod ide do `error` (stav ostáva `ok`). Vráti, či sa niečo zmenilo."""
        self._issues_checked = self.clock()
        desired = self.state.get("desired") or {}
        accounts = {a.id: a for a in (Account.from_dict(d) for d in desired.get("accounts") or [] if isinstance(d, dict))}
        deps = {d.get("id"): d for d in desired.get("deployments") or [] if isinstance(d, dict) and d.get("id")}
        changed = False
        for dep_id, entry in (self.state.get("applied") or {}).items():
            if entry.get("status") != "ok" or not entry.get("active", True) or dep_id not in deps:
                continue
            if entry.get("error") and not str(entry["error"]).startswith(ISSUE_PREFIX):
                continue
            dep = Deployment.from_dict(deps[dep_id])
            acc = accounts.get(dep.account)
            drv = self.drivers.get(acc.platform) if acc is not None else None
            if drv is None:
                continue
            if entry.get("instance"):
                dep.instance = str(entry["instance"])
            try:
                issue = drv.instance_issue(acc, dep)
            except Exception as exc:  # noqa: BLE001 - zistenie dôvodu nesmie pokaziť kolo
                self._warn_once(f"nenabehla {dep_id}", f"dôvod sa nedal zistiť: {_short(exc)}")
                continue
            error = f"{ISSUE_PREFIX}{issue}"[:500] if issue else ""
            if error:   # čas pokusu sa mení každú minútu — do logu len zmena dôvodu
                self._warn_once(f"nenabehla {dep_id}", re.sub(r" \(\d\d:\d\d:\d\d UTC\)$", "", error))
            elif self._logged.pop(f"nenabehla {dep_id}", None):
                log.info("live apply: inštancia nasadenia %s nabehla", dep_id)
            if (entry.get("error") or "") != error:
                entry["error"] = error
                changed = True
        return changed

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
        # podržané pre otvorenú pozíciu (`_hold_open`) — z hubu medzitým zmizli alebo ich hub po deaktivácii
        # zmazal, ale graf stále beží: posúdia sa znova, kým sa pozícia nezavrie
        uz = {d.id for d in vanished}
        vanished += [Deployment.from_dict(d) for i, d in (self.state.get("held") or {}).items()
                     if isinstance(d, dict) and i not in current_ids and i not in uz]
        self._held: dict[str, dict[str, Any]] = {}

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
            if acc.raw.get("secret_error"):
                account_status[acc.id]["error"] = f"hub heslo nerozšifroval: {acc.raw['secret_error']}"
                self._warn_once(f"heslo {acc.id}", account_status[acc.id]["error"])
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

        # účty s exekútorom až po ostatných: či exekútor MT5 účtu ostáva, závisí od toho, ktoré NT nasadenia naň
        # smerujúce sa v tomto kole podržali pre otvorenú pozíciu (`_hold_open` → `_held`)
        def poradie(a: str) -> tuple[bool, str]:
            return (any(d.is_executor for d in by_account.get(a, []) + vanished_by.get(a, [])), a)

        for acc_id in sorted(set(by_account) | set(vanished_by), key=poradie):
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
            # inštancie, ktoré si drží aktívne nasadenie účtu: rušené nasadenie s tým istým id (zmazané
            # a hneď znova vytvorené) ich nesmie prepnúť na `paused` — nové by bez zmeny podpisu už control
            # nikdy neprepísalo a EA by ostala v pauze
            kept = self._kept_instances(drv, acc, deps)
            for dep in deps:
                entry = self._entry(dep, "ok", "")
                predtym = prev_applied.get(dep.id) or {}
                try:
                    dep.instance = drv.instance_of(acc, dep)
                    entry["instance"] = dep.instance
                    if not dep.active:
                        self._retire_old_instance(drv, acc, dep, predtym, kept)
                        if dep.instance not in kept and self._hold_open(drv, dep, entry, active_ok):
                            applied[dep.id] = entry
                            continue
                        if dep.instance not in kept:
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
                        self._retire_old_instance(drv, acc, dep, predtym, kept)
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
                    if drv.instance_of(acc, dep) in kept:
                        log.info("live apply: nasadenie %s z hubu zmizlo, jeho inštanciu drží iné aktívne — ostáva", dep.id)
                        continue
                    dep.instance = drv.instance_of(acc, dep)
                    entry = self._entry(dep, "ok", "")
                    if self._hold_open(drv, dep, entry, active_ok):
                        applied[dep.id] = entry   # nasadenie sa v stave drží, kým sa pozícia nezavrie
                        continue
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

        self.state["held"] = self._held
        self.state["desired"] = {"accounts": [_scrub(a) for a in desired.get("accounts") or [] if isinstance(a, dict)],
                                 "deployments": [d for d in desired.get("deployments") or [] if isinstance(d, dict)]}
        self.state["applied"] = applied
        self.state["accounts"] = account_status
        self.state["secret_ack"] = secret_ack
        self.state["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._check_issues()
        self._save()

    def _hold_open(self, drv: Driver, dep: Deployment, entry: dict[str, Any], active_ok: list[Deployment]) -> bool:
        """Rušené nasadenie, ktorého inštancia má otvorenú pozíciu: graf ostane v pauze (alebo vo flatten, keď
        ho tak človek nastavil) — EA pozíciu dovedie stopom, cieľom, trailingom a EOD, len neotvorí novú.
        Odobratie grafu a reštart terminálu by pozíciu nechali bez správy (audit N-LIVE-15). True = podržané.
        Exekútor MT5 účtu nemá spool ani pozíciu — drží sa, kým naň smeruje podržané NT nasadenie (ROUTING audit H2):
        bez neho by `close`, trailing a `life` podržanej pozície nemal kto vykonať."""
        if dep.is_executor:
            routed = sorted(i for i, h in self._held.items()
                            if isinstance(h.get("route"), dict) and h["route"].get("account") == dep.account)
            if not routed:
                return False
            held = dataclasses.replace(dep, active=True)
            entry["held"] = f"naň smeruje podržané nasadenie {', '.join(routed)} s otvorenou pozíciou — exekútor ostáva"
            active_ok.append(held)
            self._held[dep.id] = {**(dep.raw or dataclasses.asdict(dep)), "active": True}
            self._warn_once(f"podržané {dep.id}", entry["held"])
            return True
        try:
            pos = self.position(dep.instance)
        except Exception:  # noqa: BLE001 - pozícia sa nedá zistiť: radšej podržať, než zavrieť graf naslepo
            pos = None
            log.warning("live apply: pozícia %s sa nedá zistiť", dep.instance, exc_info=True)
        if not pos:
            return False
        held = dataclasses.replace(dep, mode="flatten" if dep.mode == "flatten" else "paused", active=True)
        entry["control"] = str(drv.write_control(held))
        entry["held"] = f"otvorená pozícia {pos:g} — graf ostáva v režime {held.mode}, odoberie sa po jej zatvorení"
        active_ok.append(held)
        self._held[dep.id] = {**(dep.raw or dataclasses.asdict(dep)), "active": True}
        self._warn_once(f"podržané {dep.id}", entry["held"])
        return True

    @staticmethod
    def _entry(dep: Deployment, status: str, error: str) -> dict[str, Any]:
        return {"deployment": dep.id, "config_hash": dep.config_hash or config_hash(dep.config),
                "mode": dep.mode, "active": dep.active, "status": status, "error": error}

    @staticmethod
    def _kept_instances(drv: Driver, acc: Account, deps: list[Deployment]) -> set[str]:
        """Id inštancií aktívnych nasadení účtu (nasadenie, ktorému id nevyjde, tu chýba — chybu ohlási cyklus)."""
        kept: set[str] = set()
        for dep in deps:
            if dep.active:
                try:
                    kept.add(drv.instance_of(acc, dep))
                except Exception:  # noqa: BLE001
                    pass
        return kept

    @staticmethod
    def _retire_old_instance(drv: Driver, acc: Account, dep: Deployment, predtym: dict[str, Any],
                             kept: set[str] = frozenset()) -> None:
        """Nasadenie malo minule iné id inštancie (zmenil sa login/server účtu): jeho starý control súbor
        by ostal ako sirota — driver ho odstráni tak, ako rušené nasadenie (pauza, zmazanie po zastavení).
        Inštanciu, ktorú drží iné aktívne nasadenie (`kept`), nechá tak."""
        old = str(predtym.get("instance") or "")
        if not old or old == dep.instance or old in kept:
            return
        log.info("live apply: nasadenie %s zmenilo inštanciu %s -> %s, stará sa odstraňuje", dep.id, old, dep.instance)
        drv.remove_instance(acc, dataclasses.replace(dep, instance=old))
