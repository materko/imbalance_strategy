"""Driver NinjaTrader 8 (docs/LIVE.md, fáza 2b) — len súbory, beh robí AddOn `TradeBotLiveAddOn`.

`Strategy` NinjaTradera sa programovo zapnúť nedá, preto driver nič nepripína: zapíše profil
(`Documents\\NinjaTrader 8\\TradeBot\\profiles\\<stratégia>\\<profil>.json`), control súbor
(`TradeBot\\control\\<inštancia>.json`) a **`TradeBot\\deploy.json`** so zoznamom inštancií účtu
(pripojenie, účet, inštrument, TF, stratégia, profil) — AddOn ho číta pri štarte NT a pri zmene mtime
a inštancie spustí/zastaví sám. Proces `NinjaTrader.exe` driver spustí, len keď nebeží (login
NT konta musí byť zapamätaný — jediný ručný krok); heslo účtu NT nemá, `store_secret` je no-op.

`deploy.json` je jeden súbor pre celý stroj (NT beží raz), s inštanciami všetkých účtov: driver
pri `ensure_instance` účtu vymení len jeho položky a ostatné ponechá.
"""

from __future__ import annotations

import json
import logging
import os
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
        from tradebot.adapters.ninjatrader.__main__ import control_dir

        instance = self.instance_of(account, deployment)
        path = control_dir(self.nt_dir()) / f"{instance}.json"
        if path.exists():
            path.unlink()
            log.info("ninjatrader driver [%s]: control súbor %s zmazaný", account.id, instance)

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
            out.append({"deployment": dep.id, "instance": self.instance_of(account, dep),
                        "connection": account.server, "account": account.login, "instrument": dep.symbol,
                        "tf": dep.tf, "strategy": dep.strategy, "profile": dep.profile})
        return out

    def ensure_instance(self, account: Account, deployments: list[Deployment]) -> None:
        current = self.read_deploy()
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
