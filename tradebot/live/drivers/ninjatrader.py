"""Driver NinjaTrader 8 (docs/LIVE.md, fáza 2b) — len súbory, beh robí AddOn `TradeBotLiveAddOn`.

`Strategy` NinjaTradera sa programovo zapnúť nedá, preto driver nič nepripína: zapíše profil
(`Documents\\NinjaTrader 8\\TradeBot\\profiles\\<stratégia>\\<profil>.json`), control súbor
(`TradeBot\\control\\<inštancia>.json`) a **`TradeBot\\deploy.json`** so zoznamom inštancií účtu
(pripojenie, účet, inštrument, TF, stratégia, profil) — AddOn ho číta pri štarte NT a pri zmene mtime
a inštancie spustí/zastaví sám. Proces `NinjaTrader.exe` driver spustí, len keď nebeží (login
NT konta musí byť zapamätaný — jediný ručný krok); heslo účtu NT nemá, `store_secret` je no-op.

`deploy.json` je jeden súbor pre celý stroj (NT beží raz), s inštanciami všetkých účtov: driver
pri `ensure_instance` účtu vymení len jeho položky a ostatné ponechá.

Control súbor rušeného nasadenia: stratégia berie **chýbajúci súbor ako `enabled`**, preto ho
`remove_instance` nemaže, ale prepne na `paused` a odloží; zmaže sa v `ensure_instance` až po tom,
čo inštancia z `deploy.json` zmizla v niektorom z minulých kôl (AddOn ju medzitým zastavil).

Prečo inštancia nenabehla (účet nie je Connected, pripojenie, inštrument, profil, engine), AddOn píše len
do `TradeBot\\logs\\addon_*.txt` — `instance_issue` to z konca najnovšieho logu vytiahne pre reconciler.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .base import Account, Deployment, Driver

__all__ = ["NinjaTraderDriver", "DRIVER"]

log = logging.getLogger(__name__)

EXE_NAME = "NinjaTrader.exe"
#: Koľko z konca addon logu sa číta (riadky štartu inštancie sú pri konci; celý log môže mať megabajty).
LOG_TAIL_BYTES = 256 * 1024

#: Riadok `TradeBot\logs\addon_*.txt`: `<UTC čas> [<inštancia alebo nasadenie>] <text>`; riadky AddOnu bez značky.
_LOG_LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(?:\.\d+)? (?:\[([^\]]*)\] )?(.*)$")
#: Riadky `LiveInstance.Setup`/`Run`, po ktorých inštancia skončila bez obchodovania (AddOn ju skúsi znova).
_LOG_FAIL = re.compile(r"^(neuplny zaznam v deploy\.json|profil '.*' sa nenasiel|pripojenie '.*' nie je Connected"
                       r"|ucet .* sa do \d+ s nepripojil|instrument '.*' NinjaTrader nepozna|engine '.*' sa nepostavil"
                       r"|BarsRequest \d+m( bez odpovede| chyba|: )|vlakno instancie spadlo)")
#: Koniec `Setup` — predhistória prehratá, inštancia beží nazivo.
_LOG_OK = re.compile(r"^predhistoria prehrata")


def _atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class NinjaTraderDriver(Driver):
    platform = "ninjatrader"

    def __init__(self, *, nt_dir: Path | None = None, exe: Path | None = None,
                 is_running: Callable[[], bool] | None = None, launcher: Callable[[Path], int] | None = None,
                 autostart: bool | None = None) -> None:
        self._nt_dir = Path(nt_dir) if nt_dir else None
        self._exe = Path(exe) if exe else None
        self._is_running = is_running
        self._launcher = launcher
        env = os.environ.get("TRADEBOT_NT_AUTOSTART")
        self.autostart = autostart if autostart is not None else (env is None or env.strip().lower() in ("1", "true", "yes", "on"))
        #: Inštancie (podľa účtu), ktorých control súbor čaká na zmazanie, kým ich AddOn zastaví.
        self._pending_remove: dict[str, set[str]] = {}
        #: Posledné prečítané riadky addon logu: ((cesta, veľkosť, mtime), riadky).
        self._log_cache: tuple[tuple[str, int, int], list[str]] | None = None

    # -- kde je čo ------------------------------------------------------------ #

    def nt_dir(self) -> Path:
        if self._nt_dir is not None:
            return self._nt_dir
        from tradebot.adapters.ninjatrader.__main__ import find_nt_user_dir

        found = find_nt_user_dir()
        if found is None:
            raise ValueError("NinjaTrader 8 sa nenašiel (Documents\\NinjaTrader 8\\bin\\Custom); zadaj TRADEBOT_NT_DIR")
        return found

    def available(self) -> bool:
        try:
            return (self.nt_dir() / "bin" / "Custom").is_dir()
        except Exception:  # noqa: BLE001
            return False

    def exe(self) -> Path | None:
        if self._exe is not None:
            return self._exe
        for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if root and (Path(root) / "NinjaTrader 8" / "bin" / EXE_NAME).is_file():
                return Path(root) / "NinjaTrader 8" / "bin" / EXE_NAME
        return None

    def running(self) -> bool:
        if self._is_running is not None:
            return bool(self._is_running())
        if sys.platform != "win32":
            return False
        try:
            out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            return False
        return EXE_NAME.lower() in out.lower()

    def deploy_path(self) -> Path:
        return self.nt_dir() / "TradeBot" / "deploy.json"

    def spool_account(self, account: Account) -> str:
        return account.login

    # -- heslo, profil, control ---------------------------------------------- #

    def store_secret(self, account: Account, password: str) -> None:
        """NinjaTrader heslo účtu z kódu nepozná (login s „Remember“ je ručný) — nič sa neukladá."""
        log.info("ninjatrader driver [%s]: heslo sa neukladá, NT sa prihlasuje zapamätaným loginom", account.id)

    def profile_path(self, deployment: Deployment) -> Path:
        from tradebot.strategies import canonical_key

        key = canonical_key(deployment.strategy) or deployment.strategy
        return self.nt_dir() / "TradeBot" / "profiles" / key / f"{deployment.profile}.json"

    def ensure_profile(self, deployment: Deployment) -> Path:
        from tradebot.strategies import canonical_key

        key = canonical_key(deployment.strategy) or deployment.strategy
        cfg = dict(deployment.config)
        data = {"_strategy": key, "_instrument": cfg.pop("_instrument", None), "_source": f"hub:{deployment.id}",
                **{k: v for k, v in cfg.items() if k not in ("_strategy", "_source")}}
        path = self.profile_path(deployment)
        try:
            if path.is_file() and json.loads(path.read_text(encoding="utf-8")) == data:
                return path
        except (OSError, ValueError):
            pass
        _atomic_json(path, data)
        return path

    def write_control(self, deployment: Deployment) -> Path:
        from tradebot.adapters.ninjatrader.__main__ import control_dir, read_control, write_control

        nt = self.nt_dir()
        current = read_control(nt, deployment.instance)
        if current and current.get("mode") == deployment.mode and current.get("profile") == deployment.profile:
            return control_dir(nt) / f"{deployment.instance}.json"
        write_control(nt, deployment.instance, mode=deployment.mode, profile=deployment.profile, by="hub")
        return control_dir(nt) / f"{deployment.instance}.json"

    def remove_instance(self, account: Account, deployment: Deployment) -> None:
        """Nasadenie končí: control sa prepne na `paused` (kým AddOn inštanciu zastaví, nesmie otvoriť nový
        vstup; zmazaný súbor by stratégia vzala ako `enabled`) a odloží — zmaže ho `ensure_instance`, keď
        inštancia už nie je v `deploy.json`. `flatten` sa neprebíja."""
        from tradebot.adapters.ninjatrader.__main__ import read_control, write_control

        instance = self.instance_of(account, deployment)
        nt = self.nt_dir()
        current = read_control(nt, instance)
        if current is None:
            return
        if current.get("mode") not in ("paused", "flatten"):
            write_control(nt, instance, mode="paused", by="hub")
            log.info("ninjatrader driver [%s]: control %s: paused (nasadenie %s sa ruší; súbor sa zmaže, keď ju AddOn zastaví)",
                     account.id, instance, deployment.id)
        self._pending_remove.setdefault(account.id, set()).add(instance)

    def _drop_removed_controls(self, account: Account, running: set[str], wanted: set[str]) -> None:
        """Zmaže odložené control súbory inštancií, ktoré už nie sú ani v `deploy.json` z pred tohto kola
        (`running` — tie AddOn ešte len zastavuje, počkajú na ďalšie kolo), ani medzi chcenými (`wanted`)."""
        from tradebot.adapters.ninjatrader.__main__ import control_dir

        pending = self._pending_remove.get(account.id) or set()
        for inst in sorted(pending):
            if inst in wanted:
                pending.discard(inst)          # nasadenie sa vrátilo — control patrí jemu
                continue
            if inst in running:
                continue                       # AddOn ju práve zastavuje; zmazať až v ďalšom kole
            path = control_dir(self.nt_dir()) / f"{inst}.json"
            if path.exists():
                path.unlink()
                log.info("ninjatrader driver [%s]: control súbor %s zmazaný (inštancia už nie je v deploy.json)", account.id, inst)
            pending.discard(inst)
        if not pending:
            self._pending_remove.pop(account.id, None)

    # -- deploy.json ------------------------------------------------------------ #

    def read_deploy(self) -> dict[str, Any]:
        try:
            data = json.loads(self.deploy_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"instances": []}
        if not isinstance(data, dict) or not isinstance(data.get("instances"), list):
            return {"instances": []}
        return data

    def _entries(self, account: Account, deployments: list[Deployment]) -> list[dict[str, Any]]:
        out = []
        for dep in sorted(deployments, key=lambda d: d.id):
            entry = {"deployment": dep.id, "instance": self.instance_of(account, dep),
                     "connection": account.server, "account": account.login, "instrument": dep.symbol,
                     "tf": dep.tf, "strategy": dep.strategy, "profile": dep.profile}
            route = dep.route
            if route:
                # ordery do MT5 exekútora (docs/ROUTING.md) — AddOn ich pošle cez bridge, NT dá len dáta
                entry["route"] = {"via": "mt5", "to": route["to"], "symbol": route.get("symbol") or "",
                                  "price": route.get("price") or "basis", "scale": float(route.get("scale") or 1.0),
                                  "qty": dict(route.get("qty") or {"mode": "value"}), "magic": 0}
            out.append(entry)
        return out

    def ensure_instance(self, account: Account, deployments: list[Deployment]) -> None:
        current = self.read_deploy()
        bezali = {str(e.get("instance") or "") for e in current["instances"] if isinstance(e, dict)}
        mine = self._entries(account, deployments)
        cudzie = [e for e in current["instances"]
                  if isinstance(e, dict) and not (e.get("account") == account.login and e.get("connection") == account.server)]
        wanted = {"instances": cudzie + mine}
        if [e for e in current["instances"] if isinstance(e, dict)] != wanted["instances"]:
            wanted["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            wanted["by"] = "hub"
            _atomic_json(self.deploy_path(), wanted)
            log.info("ninjatrader driver [%s]: deploy.json: %d inštancií (%d tohto účtu)", account.id,
                     len(wanted["instances"]), len(mine))
        # control rušených nasadení až po deploy.json (AddOn inštanciu zastaví) — a až keď v ňom už neboli
        self._drop_removed_controls(account, bezali, {e["instance"] for e in mine})
        if mine and self.autostart and not self.running():
            self._start()

    def _start(self) -> None:
        exe = self.exe()
        if exe is None:
            raise ValueError("NinjaTrader.exe sa nenašiel (Program Files\\NinjaTrader 8\\bin)")
        if self._launcher is not None:
            self._launcher(exe)
            return
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        subprocess.Popen([str(exe)], cwd=str(exe.parent), creationflags=flags, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.info("ninjatrader driver: spustený %s", exe)

    # -- prečo inštancia nenabehla (addon log) --------------------------------- #

    def log_path(self) -> Path | None:
        """Najnovší `TradeBot\\logs\\addon_<yyyyMMdd-HHmmss>.txt` (jeden na štart NT / generáciu AddOnu)."""
        try:
            logs = sorted((self.nt_dir() / "TradeBot" / "logs").glob("addon_*.txt"))
        except OSError:
            return None
        return logs[-1] if logs else None

    def _log_lines(self) -> list[str]:
        """Posledných `LOG_TAIL_BYTES` najnovšieho addon logu po riadkoch; podľa (cesta, veľkosť, mtime)
        sa číta len raz — reconciler sa pýta každé kolo za každé nasadenie."""
        path = self.log_path()
        if path is None:
            return []
        try:
            st = path.stat()
            key = (str(path), st.st_size, st.st_mtime_ns)
            if self._log_cache is not None and self._log_cache[0] == key:
                return self._log_cache[1]
            with path.open("rb") as fh:
                if st.st_size > LOG_TAIL_BYTES:
                    fh.seek(st.st_size - LOG_TAIL_BYTES)
                    fh.readline()                      # začiatok prvého riadku je odrezaný
                lines = fh.read().decode("utf-8", errors="replace").splitlines()
        except OSError:
            return []
        self._log_cache = (key, lines)
        return lines

    def instance_issue(self, account: Account, deployment: Deployment) -> str | None:
        """Dôvod z addon logu, prečo inštancia nasadenia nenabehla (`LiveInstance.Setup` v
        TradeBotLiveInstance.cs): posledný pokus (`[<nasadenie>] start …`) skončil riadkom zlyhania →
        jeho text; prehral predhistóriu → `None`. Pokus, ktorý ešte beží (AddOn skúša znova o 60 s, na
        pripojenie a účet čaká až 2 × 60 s), nič nemení — platí výsledok predošlého pokusu."""
        tags = {deployment.id, self.instance_of(account, deployment)}
        last: str | None = None           # výsledok posledného ukončeného pokusu (None = nabehla)
        pripojenie: str | None = None     # posledný riadok AddOnu o pripojení počas pokusu (bez značky)
        for line in self._log_lines():
            m = _LOG_LINE.match(line)
            if m is None:
                continue
            cas, tag, text = m.group(1), m.group(2), m.group(3)
            if tag is None:
                if text.startswith(f"pripojenie '{account.server}'") and account.server:
                    pripojenie = text
                continue
            if tag not in tags:
                continue
            if text.startswith("start "):
                pripojenie = None
            elif _LOG_OK.match(text):
                last = None
            elif _LOG_FAIL.match(text):
                last = f"{text} ({cas[11:19]} UTC)"
                if pripojenie and "nie je Connected" in text:
                    last = f"{text} — {pripojenie} ({cas[11:19]} UTC)"
        return last[:400] if last else None

    def status(self, account: Account) -> dict[str, Any]:
        data = self.read_deploy()
        return {"platform": self.platform, "running": self.running(), "deploy": str(self.deploy_path()),
                "instances": [e for e in data["instances"] if isinstance(e, dict) and e.get("account") == account.login],
                "updated": data.get("updated"), "installed": self.installed_version()}

    # -- kód platformy (docs/LIVE.md, fáza 2c) --------------------------------- #

    def installed_version(self) -> str | None:
        """Commit z `TradeBot\\installed.json`; marker s `compiled: false` (zdrojáky nakopírované, NT ich
        nepreložil) sa nepočíta — na platforme ešte beží starý kód."""
        from tradebot.adapters.ninjatrader.__main__ import read_installed

        try:
            data = read_installed(self.nt_dir())
        except Exception:  # noqa: BLE001
            return None
        if not data or data.get("compiled") is False:
            return None
        return str(data.get("version") or "") or None

    def install_code(self, version: str, accounts: list[Account]) -> dict[str, Any]:
        """`install` (zdrojáky jadra, AddOn, adaptér, šablóny, profily do `bin\\Custom`) a preklad bez človeka
        (`nt_compile`: MSBuild, potom F5 v NinjaScript Editore bežiaceho NT). Po preklade NT sám inštancuje
        AddOn znova (nová generácia) a bežiace inštancie z `deploy.json` nabehnú v novej session — driver nič
        nezastavuje. Keď NT nebeží, zdrojáky sú na disku, ale marker má `compiled: false` a hlási sa chyba
        (preklad urobí až človek F5, alebo ďalší pokus pri bežiacom NT)."""
        from tradebot.adapters.ninjatrader.__main__ import InstallError, install, nt_compile, write_installed

        nt = self.nt_dir()
        out: dict[str, Any] = {"nt_dir": str(nt), "nt_running": self.running()}
        out["install"] = install(nt, [], say=lambda t: log.info("ninjatrader driver: %s", t.replace("\n", " | ")),
                                 version=version, by="hub", compiled=False)
        if not out["nt_running"]:
            raise InstallError("NinjaTrader nebeží — zdrojáky sú nakopírované, preklad (F5) urobí až bežiaci NT; "
                               "spusti NT (login je ručný) a aktualizáciu zopakuj")
        comp = nt_compile(nt)
        out["compile"] = {k: v for k, v in comp.items() if k != "attempts"}
        out["compile"]["attempts"] = [{"method": a.get("method"), "ok": a.get("ok"), "error": a.get("error")}
                                      for a in comp.get("attempts") or []]
        out["compiled"] = bool(comp.get("ok"))
        out["generation"] = comp.get("generation")
        write_installed(nt, version, by="hub", compiled=out["compiled"])
        if not out["compiled"]:
            raise InstallError("zdrojáky nakopírované, ale preklad bez človeka neprešiel: " + str(comp.get("error") or "?"))
        log.info("ninjatrader driver: kód %s nasadený, preklad %s, generácia AddOnu %s", version, comp.get("method"),
                 comp.get("generation") or "?")
        return out


DRIVER = NinjaTraderDriver()
