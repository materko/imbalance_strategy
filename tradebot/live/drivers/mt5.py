"""Driver MetaTrader 5 (docs/LIVE.md, fáza 2b; docs/MT5.md „Nasadenie z hubu“).

Jeden účet = jedna inštancia terminálu. Driver pre účet drží `tester/live/mt5/<account>/`:

    start.ini       štartovací ini (`/config:`): [Common] Login/Server[/Password], [Charts] ProfileLast=tradebot,
                    [Experts] AllowLiveTrading/AllowDllImport/Enabled — heslo tam je len do prihlásenia
    terminal.pid    {"pid", "started"} procesu, ktorý driver spustil
    charts.json     manifest grafov, ktoré profil `tradebot` má mať (porovnanie = idempotencia)
    driver.log      čo driver s terminálom robil
    terminal/       portable kópia terminálu (len keď účet nemá `terminal` a má `portable`)

Grafy s EA nie sú v `[StartUp]` (ten pripne jeden EA a po reštarte sa neobnoví), ale v **profile
grafov** terminálu `MQL5\\Profiles\\Charts\\tradebot\\chartNN.chr` + `order.wnd` (UTF-16 LE s BOM, CRLF —
presne ako ich terminál sám ukladá): symbol, perióda, EA `Experts\\TradeBot\\<Šablóna>.ex5` a jeho
inputy. Terminál profil otvorí, lebo ini hovorí `[Charts] ProfileLast=tradebot`, a pri vypnutí ho
sám prepíše (pridá objekty, prečísluje) — preto sa zhoda neporovnáva textovo, ale podľa toho, čo
v súboroch je (symbol, perióda, EA, `InpProfile`, `InpMagic`).

Zmena množiny grafov (nové nasadenie, odobraté, iný config profilu) = slušne zavrieť terminál
(`taskkill` bez `/F`, EA dostane `OnDeinit`, spool `bye`), prepísať profil, spustiť znova. Režim
(`paused`/`flatten`) a zmena názvu profilu idú cez control súbor bez reštartu. Keď stav sedí a
terminál beží, `ensure_instance` nerobí nič; keď nebeží (pád, človek ho zavrel), spustí ho.

Poradie okolo control súboru je vec bezpečnosti — EA berie **chýbajúci súbor ako `enabled`**:

- pred štartom terminálu má každý graf control súbor s režimom nasadenia (reconciler ho píše pred
  `ensure_instance`; driver to pred `_start` ešte skontroluje a chýbajúci dopíše),
- rušené nasadenie (`remove_instance`) sa najprv prepne na `paused`, control ostáva, kým terminál
  s tým grafom beží; zmaže sa až v `ensure_instance` **po** zavretí terminálu (`_drop_removed_controls`).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tradebot.core.paths import LIVE_MT5_DIR, LIVE_SECRETS, MT5_DIR

from . import secrets
from .base import Account, Deployment, Driver

__all__ = ["Mt5Driver", "DRIVER", "magic_for", "templates", "ea_inputs", "chart_text", "parse_chart", "period_of"]

log = logging.getLogger(__name__)

PROFILE_NAME = "tradebot"
EXE_NAME = "terminal64.exe"
#: Koľko sekúnd čakať na slušné vypnutie terminálu, kým sa zabije natvrdo; slušné zavretie sa
#: medzitým opakuje každých `CLOSE_RETRY` s (terminál v štarte ešte okno nemá a prvé nevidí).
CLOSE_TIMEOUT = 60.0
CLOSE_RETRY = 10.0
#: Po toľkých sekundách od štartu je terminál prihlásený a heslo sa z ini zmaže.
PASSWORD_TTL = 30.0
#: Čo z inštalácie terminálu tvorí portable kópiu (Bases si terminál stiahne sám, MetaEditor netreba).
PORTABLE_ITEMS = (EXE_NAME, "Config", "Profiles", "Sounds", "Terminal.ico")
#: Čo z dátového adresára zdrojového terminálu potrebuje portable kópia (nasadené jadro a EA).
PORTABLE_MQL5 = (("Libraries", "TradeBot.dll"), ("Include", "TradeBot"), ("Experts", "TradeBot"), ("Presets",))
#: Inputy EA, ktoré driver určuje sám — čokoľvek v `<Šablóna>_live.set` neprebije.
FORCED_INPUTS = {"InpTelemetry": True, "InpTelemetryInTester": False, "InpExportSignals": False,
                 "InpScreenshotFile": "", "InpCloseAfterShot": False}

_INPUT_RE = re.compile(r"^\s*(?:s?input)\s+(\w+)\s+(\w+)\s*=\s*(.*?)\s*;", re.M)
_KEY_RE = re.compile(r'#define\s+TRADEBOT_ENGINE_KEY\s+"([^"]+)"')


# ------------------------------------------------------------------------------------------------ #
# čisté funkcie: šablóny, inputy, magic, text profilu grafov
# ------------------------------------------------------------------------------------------------ #

def templates(deploy_dir: Path | None = None) -> dict[str, str]:
    """Kľúč enginu → názov šablóny EA (`ibsnet` → `IBSNet`) z `#define TRADEBOT_ENGINE_KEY` v `deploy/mt5/*.mq5`."""
    out: dict[str, str] = {}
    for src in sorted((deploy_dir or MT5_DIR).glob("*.mq5")):
        try:
            m = _KEY_RE.search(src.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if m:
            out[m.group(1)] = src.stem
    return out


def _read_text_any(path: Path) -> str:
    """Terminál píše UTF-16 LE s BOM, repozitár UTF-8 — obe."""
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe"):
        return data.decode("utf-16-le")[1:]
    return data.decode("utf-8-sig", errors="replace")


def ea_inputs(ea_source: Path | None = None) -> list[tuple[str, str, str]]:
    """`(typ, názov, predvolená hodnota)` všetkých `input` z `TradeBotEA.mqh` v poradí deklarácie."""
    src = ea_source or Path(__file__).resolve().parents[2] / "adapters" / "mt5" / "TradeBotEA.mqh"
    text = src.read_text(encoding="utf-8", errors="replace")
    return [(t, n, v) for t, n, v in _INPUT_RE.findall(text)]


def _set_values(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in _read_text_any(path).splitlines():
        if "=" in line and not line.startswith((";", "#")):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _fmt_input(typ: str, value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if typ == "bool":
        return "true" if str(value).strip().lower() in ("true", "1") else "false"
    if typ == "string":
        text = str(value)
        return text[1:-1] if len(text) >= 2 and text[0] == text[-1] == '"' else text
    if typ == "double":
        try:
            return repr(float(str(value)))
        except ValueError:
            return str(value)
    try:
        return str(int(float(str(value))))
    except ValueError:
        return str(value)


def magic_for(deployment_id: str) -> int:
    """Magic number EA z id nasadenia — deterministický, kladný, < 2^31; rôzne nasadenia na jednom účte
    tak majú rôzne magic (EA podľa neho pozná svoje ordery)."""
    h = int(hashlib.sha256(str(deployment_id).encode("utf-8")).hexdigest()[:8], 16)
    return 100_000 + h % 2_000_000_000


def period_of(tf_minutes: int) -> tuple[int, int]:
    """TF v minútach → `(period_type, period_size)` ako v `.chr`: 0 = minúty, 1 = hodiny, 2 = dni."""
    tf = int(tf_minutes)
    if tf >= 1440 and tf % 1440 == 0:
        return 2, tf // 1440
    if tf >= 60 and tf % 60 == 0:
        return 1, tf // 60
    return 0, tf


def chart_id(instance: str) -> int:
    return int(hashlib.sha256(instance.encode("utf-8")).hexdigest()[:15], 16) or 1


_CHART_HEAD = (
    "scale_fix=0", "scale_fixed_min=0.000000", "scale_fixed_max=0.000000", "scale_fix11=0", "scale_bar=0",
    "scale_bar_val=0.000000", "scale=4", "mode=1", "fore=0", "grid=1", "volume=0", "scroll=1", "shift=1",
    "shift_size=20.000000", "fixed_pos=0.000000", "ticker=1", "ohlc=0", "one_click=0", "one_click_btn=1",
    "bidline=1", "askline=0", "lastline=0", "days=0", "descriptions=0", "tradelines=1", "tradehistory=1",
)
_CHART_TAIL = (
    "window_type=1", "floating=0", "floating_left=0", "floating_top=0", "floating_right=0", "floating_bottom=0",
    "floating_type=1", "floating_toolbar=1", "floating_tbstate=", "background_color=0",
    "foreground_color=16777215", "barup_color=65280", "bardown_color=65280", "bullcandle_color=0",
    "bearcandle_color=16777215", "chartline_color=65280", "volumes_color=3329330", "grid_color=10061943",
    "bidline_color=10061943", "askline_color=255", "lastline_color=49152", "stops_color=255", "windows_total=1",
)
_MAIN_INDICATOR = (
    "<indicator>", "name=Main", "path=", "apply=1", "show_data=1", "scale_inherit=0", "scale_line=0",
    "scale_line_percent=50", "scale_line_value=0.000000", "scale_fix_min=0", "scale_fix_min_val=0.000000",
    "scale_fix_max=0", "scale_fix_max_val=0.000000", "expertmode=0", "fixed_height=-1", "</indicator>",
)


def chart_text(chart: dict[str, Any], index: int) -> str:
    """Obsah `chartNN.chr` (bez BOM, riadky bez CRLF — tie dodá zápis) pre jeden graf s EA.
    Tvar je z profilu, ktorý terminál build 6230 uložil sám; `window_*` dlaždicuje grafy pod seba."""
    ptype, psize = period_of(chart["tf"])
    top = 300 * index
    lines = [
        "<chart>", f"id={chart_id(chart['instance'])}", f"symbol={chart['symbol']}",
        f"period_type={ptype}", f"period_size={psize}", *_CHART_HEAD,
        "window_left=0", f"window_top={top}", "window_right=1400", f"window_bottom={top + 300}", *_CHART_TAIL,
        "", "<expert>", f"name={chart['expert']}", f"path={chart['path']}", "expertmode=4", "<inputs>",
        *[f"{k}={v}" for k, v in chart["inputs"].items()],
        "</inputs>", "</expert>", "", "<window>", "height=100.000000", "objects=0", "", *_MAIN_INDICATOR, "",
        "</window>", "</chart>",
    ]
    return "\n".join(lines)


def _write_utf16(path: Path, text: str, trailing_newline: bool) -> None:
    body = text.replace("\r\n", "\n").replace("\n", "\r\n")
    if trailing_newline and not body.endswith("\r\n"):
        body += "\r\n"
    path.write_bytes(b"\xff\xfe" + body.encode("utf-16-le"))


def parse_chart(path: Path) -> dict[str, Any] | None:
    """Z `.chr` to, čo identifikuje graf s EA: symbol, perióda, cesta EA a jeho inputy; `None` bez EA."""
    try:
        text = _read_text_any(path)
    except OSError:
        return None
    out: dict[str, Any] = {"symbol": "", "period_type": 0, "period_size": 0, "path": "", "inputs": {}}
    section = "chart"
    for raw in text.splitlines():
        line = raw.strip()
        if line in ("<expert>", "<inputs>", "<window>", "<indicator>", "<object>"):
            section = line[1:-1]
            continue
        if line.startswith("</"):
            section = "expert" if line == "</inputs>" else "chart" if line in ("</expert>", "</window>") else section
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if section == "chart" and k in ("symbol", "period_type", "period_size"):
            out[k] = int(v) if k != "symbol" else v
        elif section == "expert" and k == "path":
            out["path"] = v
        elif section == "inputs":
            out["inputs"][k] = v
    return out if out["path"] else None


def _chart_key(symbol: str, tf: int, path: str, profile: str, magic: int) -> tuple:
    return (symbol, period_of(tf), path.lower(), profile, int(magic))


# ------------------------------------------------------------------------------------------------ #
# procesy (Windows) — oddelené, aby sa dali v testoch podstrčiť
# ------------------------------------------------------------------------------------------------ #

class WindowsProcesses:
    """`tasklist`/`taskkill`/`Popen` — bez ďalších závislostí."""

    def alive(self, pid: int) -> bool:
        if not pid:
            return False
        try:
            out = subprocess.run(["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            return False
        return EXE_NAME.lower() in out.lower()

    def find(self, exe: Path) -> list[int]:
        """PID-y `terminal64.exe` spustené z tohto `exe` (iné portable kópie sa nepočítajú)."""
        try:
            ps = ("Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
                  "ForEach-Object { \"$($_.Id)|$($_.Path)\" }")
            out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                                 capture_output=True, text=True, timeout=60).stdout
        except (OSError, subprocess.SubprocessError):
            return []
        pids = []
        for line in out.splitlines():
            if "|" not in line:
                continue
            pid, path = line.split("|", 1)
            try:
                if os.path.normcase(path.strip()) == os.path.normcase(str(exe)):
                    pids.append(int(pid))
            except ValueError:
                continue
        return pids

    def close(self, pid: int, force: bool = False) -> None:
        cmd = ["taskkill", "/PID", str(int(pid))] + (["/F"] if force else [])
        subprocess.run(cmd, capture_output=True, timeout=30)

    def start(self, cmd: list[str], cwd: Path) -> int:
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(cmd, cwd=str(cwd), creationflags=flags, close_fds=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.pid


# ------------------------------------------------------------------------------------------------ #
# driver
# ------------------------------------------------------------------------------------------------ #

class Mt5Driver(Driver):
    platform = "mt5"

    def __init__(self, *, root: Path | None = None, secrets_root: Path | None = None, exe: Path | None = None,
                 data_dir: Path | None = None, common: Path | None = None, processes: Any = None,
                 sleep: Callable[[float], None] = time.sleep, allow_live_trading: bool | None = None,
                 deploy_dir: Path | None = None, ea_source: Path | None = None, clock=time.time) -> None:
        self.root = Path(root or LIVE_MT5_DIR)
        self.secrets_root = Path(secrets_root or LIVE_SECRETS)
        #: Nainštalovaný terminál (účty bez vlastného `terminal`): `TRADEBOT_MT5_TERMINAL`, `origin.txt`, Program Files.
        self._exe = Path(exe) if exe else None
        self._data_dir = Path(data_dir) if data_dir else None
        self._common = Path(common) if common else None
        self.processes = processes or WindowsProcesses()
        self.sleep = sleep
        self.clock = clock
        env = os.environ.get("TRADEBOT_MT5_ALLOW_LIVE_TRADING")
        self.allow_live_trading = (allow_live_trading if allow_live_trading is not None
                                   else env is None or env.strip().lower() in ("1", "true", "yes", "on"))
        self.deploy_dir = Path(deploy_dir) if deploy_dir else None
        self.ea_source = Path(ea_source) if ea_source else None
        self._templates: dict[str, str] | None = None
        self._inputs: list[tuple[str, str, str]] | None = None
        #: Inštancie (podľa účtu), ktorých control súbor čaká na zmazanie, kým terminál s ich grafom zavrie.
        self._pending_remove: dict[str, set[str]] = {}

    # -- kde je čo ------------------------------------------------------------ #

    def available(self) -> bool:
        if sys.platform != "win32" and self._exe is None:
            return False
        try:
            return self._installed_exe() is not None
        except Exception:  # noqa: BLE001
            return False

    def _installed_exe(self) -> Path | None:
        if self._exe is not None:
            return self._exe if self._exe.is_file() else None
        raw = os.environ.get("TRADEBOT_MT5_TERMINAL")
        if raw and Path(raw).is_file():
            return Path(raw)
        from tradebot.adapters.mt5.__main__ import candidate_dirs

        for mql5 in candidate_dirs():
            origin = mql5.parent / "origin.txt"
            try:
                if origin.exists():
                    exe = Path(_read_text_any(origin).strip()) / EXE_NAME
                    if exe.is_file():
                        return exe
            except OSError:
                continue
        for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if root:
                for found in Path(root).glob(f"*/{EXE_NAME}"):
                    return found
        return None

    def _data_dir_for(self, exe: Path) -> Path:
        """Dátový adresár nainštalovaného (nie portable) terminálu: `TRADEBOT_MT5_DIR`, inak ten
        z `%APPDATA%\\MetaQuotes\\Terminal\\<hash>`, ktorého `origin.txt` ukazuje na `exe`."""
        if self._data_dir is not None:
            return self._data_dir
        raw = os.environ.get("TRADEBOT_MT5_DIR")
        if raw:
            p = Path(raw)
            return p.parent if p.name == "MQL5" else p
        from tradebot.adapters.mt5.__main__ import candidate_dirs

        found = candidate_dirs()
        for mql5 in found:
            origin = mql5.parent / "origin.txt"
            try:
                if origin.exists() and os.path.normcase(_read_text_any(origin).strip()) == os.path.normcase(str(exe.parent)):
                    return mql5.parent
            except OSError:
                continue
        if len(found) == 1:
            return found[0].parent
        raise ValueError(f"dátový adresár terminálu {exe} sa nenašiel v %APPDATA%\\MetaQuotes\\Terminal; zadaj TRADEBOT_MT5_DIR")

    def common(self) -> Path:
        if self._common is not None:
            return self._common
        from tradebot.adapters.mt5.__main__ import find_common_files

        spolocny = find_common_files()
        if spolocny is None:
            raise ValueError("Common\\Files MetaTrader 5 sa nenašiel (%APPDATA%\\MetaQuotes\\Terminal\\Common\\Files)")
        return spolocny

    def account_dir(self, account: Account) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in account.id) or "ucet"
        return self.root / safe

    def terminal_for(self, account: Account) -> tuple[Path, Path, bool]:
        """`(terminal64.exe, dátový adresár, portable)` účtu: daný `terminal` (súbor alebo adresár),
        portable kópia v `tester/live/mt5/<account>/terminal/` (vznikne pri prvom použití), alebo
        nainštalovaný terminál stroja."""
        raw = account.terminal.strip()
        if raw:
            p = Path(raw)
            exe = p if p.suffix.lower() == ".exe" else p / EXE_NAME
            if not exe.is_file():
                raise ValueError(f"terminál účtu {account.id}: {exe} nie je")
            if account.portable:
                return exe, exe.parent, True
            return exe, self._data_dir_for(exe), False
        if account.portable:
            dst = self.account_dir(account) / "terminal"
            exe = dst / EXE_NAME
            if not exe.is_file():
                self._make_portable(account, dst)
            return exe, dst, True
        exe = self._installed_exe()
        if exe is None:
            raise ValueError("terminal64.exe sa nenašiel (Program Files, origin.txt); zadaj TRADEBOT_MT5_TERMINAL "
                             "alebo účtu cestu `terminal`")
        return exe, self._data_dir_for(exe), False

    def _make_portable(self, account: Account, dst: Path) -> None:
        """Portable kópia: `terminal64.exe` + Config/Profiles/Sounds z inštalácie (bez Bases — históriu si
        stiahne, bez MetaEditora) a nasadené jadro/EA/presety z dátového adresára zdrojového terminálu.
        Spúšťa sa s `/portable`, dáta má pri sebe. Neoverené naživo (na tomto stroji je jeden účet)."""
        src_exe = self._installed_exe()
        if src_exe is None:
            raise ValueError("portable kópia: zdrojový terminal64.exe sa nenašiel")
        self._log(account, f"portable kópia z {src_exe.parent} -> {dst}")
        dst.mkdir(parents=True, exist_ok=True)
        for item in PORTABLE_ITEMS:
            s = src_exe.parent / item
            if s.is_dir():
                shutil.copytree(s, dst / item, dirs_exist_ok=True)
            elif s.is_file():
                shutil.copy2(s, dst / item)
        try:
            src_data = self._data_dir_for(src_exe)
        except ValueError:
            return
        for parts in PORTABLE_MQL5:
            s = src_data.joinpath("MQL5", *parts)
            d = dst.joinpath("MQL5", *parts)
            if s.is_dir():
                shutil.copytree(s, d, dirs_exist_ok=True)
            elif s.is_file():
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
        servers = src_data / "config" / "servers.dat"
        if servers.is_file():
            (dst / "config").mkdir(exist_ok=True)
            shutil.copy2(servers, dst / "config" / "servers.dat")

    def spool_account(self, account: Account) -> str:
        return f"{account.login}-{account.server}"

    # -- log ----------------------------------------------------------------- #

    def _log(self, account: Account, text: str) -> None:
        log.info("mt5 driver [%s]: %s", account.id, text)
        try:
            d = self.account_dir(account)
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "driver.log", "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} {text}\n")
        except OSError:
            pass

    # -- heslo, profil, control ---------------------------------------------- #

    def store_secret(self, account: Account, password: str) -> None:
        secrets.store(account.id, password, self.secrets_root)
        self._log(account, "heslo uložené (DPAPI)")

    def template_for(self, strategy: str) -> tuple[str, str]:
        """`(názov EA, cesta v profile)` pre kľúč enginu — z `deploy/mt5/*.mq5`, nie z tabuľky v kóde."""
        if self._templates is None:
            self._templates = templates(self.deploy_dir)
        from tradebot.strategies import canonical_key

        key = canonical_key(strategy) or strategy
        name = self._templates.get(key)
        if not name:
            raise ValueError(f"stratégia {strategy!r} nemá šablónu EA v deploy/mt5 (známe: {sorted(self._templates)})")
        return name, f"Experts\\TradeBot\\{name}.ex5"

    def profile_path(self, deployment: Deployment) -> Path:
        from tradebot.strategies import canonical_key

        key = canonical_key(deployment.strategy) or deployment.strategy
        return self.common() / "TradeBot" / "profiles" / key / f"{deployment.profile}.json"

    def ensure_profile(self, deployment: Deployment) -> Path:
        from tradebot.strategies import canonical_key

        key = canonical_key(deployment.strategy) or deployment.strategy
        cfg = dict(deployment.config)
        data = {"_strategy": key, "_instrument": cfg.pop("_instrument", None),
                "_source": f"hub:{deployment.id}", **{k: v for k, v in cfg.items() if k not in ("_strategy", "_source")}}
        path = self.profile_path(deployment)
        try:
            if path.is_file() and json.loads(path.read_text(encoding="utf-8")) == data:
                return path
        except (OSError, ValueError):
            pass
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return path

    def write_control(self, deployment: Deployment) -> Path:
        from tradebot.adapters.mt5.__main__ import control_dir, read_control, write_control

        common = self.common()
        instance = deployment.instance
        current = read_control(common, instance)
        if current and current.get("mode") == deployment.mode and current.get("profile") == deployment.profile:
            return control_dir(common) / f"{instance}.json"
        write_control(common, instance, deployment.mode, deployment.profile, by="hub")
        return control_dir(common) / f"{instance}.json"

    def remove_instance(self, account: Account, deployment: Deployment) -> None:
        """Nasadenie končí: kým terminál s jeho grafom beží, EA nesmie otvoriť nový vstup — control sa
        prepne na `paused` (zmazaný súbor by EA vzala ako `enabled`) a odloží na zmazanie; zmaže ho až
        `ensure_instance` po zavretí terminálu (`_drop_removed_controls`). `flatten` sa neprebíja."""
        from tradebot.adapters.mt5.__main__ import read_control, write_control

        instance = self.instance_of(account, deployment)
        common = self.common()
        current = read_control(common, instance)
        if current is None:
            return
        if current.get("mode") not in ("paused", "flatten"):
            write_control(common, instance, "paused", None, by="hub")
            self._log(account, f"control {instance}: paused (nasadenie {deployment.id} sa ruší; súbor sa zmaže "
                               f"po zavretí terminálu)")
        self._pending_remove.setdefault(account.id, set()).add(instance)

    def _ensure_controls(self, account: Account, deployments: list[Deployment]) -> None:
        """Pred štartom terminálu má každý graf control súbor s režimom nasadenia — bez neho by EA
        naštartovala `enabled`. Reconciler ho píše pred `ensure_instance`; toto je poistka."""
        from tradebot.adapters.mt5.__main__ import read_control, write_control

        common = self.common()
        for dep in deployments:
            instance = self.instance_of(account, dep)
            if read_control(common, instance) is None:
                write_control(common, instance, dep.mode, dep.profile, by="hub")
                self._log(account, f"control {instance}: {dep.mode} dopísaný pred štartom (chýbal)")

    # -- grafy --------------------------------------------------------------- #

    def chart_inputs(self, deployment: Deployment, expert: str) -> dict[str, str]:
        """Inputy EA pre graf: predvolené z `TradeBotEA.mqh`, cez ne `<Šablóna>_live.set` (posun servera…),
        cez to profil, magic a telemetria od drivera."""
        if self._inputs is None:
            self._inputs = ea_inputs(self.ea_source)
        presets = Path(__file__).resolve().parents[2] / "adapters" / "mt5" / "presets"
        live = _set_values(presets / f"{expert}_live.set")
        forced: dict[str, Any] = {"InpProfile": deployment.profile, "InpMagic": magic_for(deployment.id), **FORCED_INPUTS}
        out: dict[str, str] = {}
        for typ, name, default in self._inputs:
            if name in forced:
                value: Any = forced[name]
            elif name in live:
                value = live[name]
            elif name == "InpProfile":
                value = deployment.profile
            else:
                value = default
            out[name] = _fmt_input(typ, value)
        return out

    def _charts(self, account: Account, deployments: list[Deployment]) -> list[dict[str, Any]]:
        charts = []
        for dep in sorted(deployments, key=lambda d: d.id):
            expert, path = self.template_for(dep.strategy)
            instance = self.instance_of(account, dep)
            charts.append({"deployment": dep.id, "instance": instance, "symbol": dep.symbol, "tf": dep.tf,
                           "strategy": dep.strategy, "profile": dep.profile, "config_hash": dep.config_hash,
                           "expert": expert, "path": path, "magic": magic_for(dep.id),
                           "inputs": self.chart_inputs(dep, expert)})
        return charts

    @staticmethod
    def _charts_key(charts: list[dict[str, Any]]) -> list[list[Any]]:
        return sorted([c["symbol"], list(period_of(c["tf"])), c["path"].lower(), c["profile"], int(c["magic"]),
                       c.get("config_hash") or ""] for c in charts)

    def profile_dir(self, data_dir: Path) -> Path:
        return data_dir / "MQL5" / "Profiles" / "Charts" / PROFILE_NAME

    def _profile_on_disk(self, data_dir: Path) -> set[tuple]:
        out: set[tuple] = set()
        folder = self.profile_dir(data_dir)
        if not folder.is_dir():
            return out
        for f in sorted(folder.glob("*.chr")):
            ch = parse_chart(f)
            if ch is None:
                continue
            try:
                magic = int(float(ch["inputs"].get("InpMagic", "0")))
            except ValueError:
                magic = 0
            out.add((ch["symbol"], (ch["period_type"], ch["period_size"]), ch["path"].lower(),
                     ch["inputs"].get("InpProfile", ""), magic))
        return out

    def _profile_matches(self, data_dir: Path, charts: list[dict[str, Any]]) -> bool:
        wanted = {_chart_key(c["symbol"], c["tf"], c["path"], c["profile"], c["magic"]) for c in charts}
        return self._profile_on_disk(data_dir) == wanted

    def write_chart_profile(self, data_dir: Path, charts: list[dict[str, Any]]) -> Path:
        """Profil `tradebot` nanovo: staré `chartNN.chr` preč, jeden súbor na graf, `order.wnd` ako terminál
        (posledný graf prvý). Prázdny zoznam = profil bez grafov (terminál otvorí prázdnu plochu)."""
        folder = self.profile_dir(data_dir)
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.chr"):
            old.unlink()
        names = []
        for i, chart in enumerate(charts):
            name = f"chart{i + 1:02d}.chr"
            _write_utf16(folder / name, chart_text(chart, i), trailing_newline=False)
            names.append(name)
        _write_utf16(folder / "order.wnd", "\n".join(reversed(names)) + ("\n" if names else ""), trailing_newline=False)
        return folder

    # -- ini a proces ----------------------------------------------------------- #

    def ini_text(self, account: Account, password: str | None) -> str:
        lines = [f"; TradeBot live driver: ucet {account.id} ({account.label}) - generovane, neupravovat",
                 "[Common]", f"Login={account.login}", f"Server={account.server}"]
        if password:
            lines.append(f"Password={password}")
        lines += ["[Charts]", f"ProfileLast={PROFILE_NAME}", "[Experts]",
                  f"AllowLiveTrading={1 if self.allow_live_trading else 0}", "AllowDllImport=1", "Enabled=1"]
        return "\n".join(lines) + "\n"

    def _write_ini(self, account: Account, with_password: bool) -> Path:
        d = self.account_dir(account)
        d.mkdir(parents=True, exist_ok=True)
        heslo = None
        if with_password:
            try:
                heslo = secrets.load(account.id, self.secrets_root)
            except OSError as exc:
                self._log(account, f"heslo sa nedá prečítať: {exc} — štart bez hesla (terminál použije uložené)")
        path = d / "start.ini"
        path.write_text(self.ini_text(account, heslo), encoding="utf-8")
        return path

    def _pid_info(self, account: Account) -> dict[str, Any]:
        try:
            data = json.loads((self.account_dir(account) / "terminal.pid").read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _running_pid(self, account: Account) -> int | None:
        info = self._pid_info(account)
        pid = int(info.get("pid") or 0)
        return pid if pid and self.processes.alive(pid) else None

    def _manifest(self, account: Account) -> dict[str, Any] | None:
        try:
            data = json.loads((self.account_dir(account) / "charts.json").read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, ValueError):
            return None

    def _close(self, account: Account, pid: int) -> None:
        self._log(account, f"zatváram terminál PID {pid} (taskkill bez /F)")
        self.processes.close(pid)
        t0 = last = self.clock()
        while self.processes.alive(pid):
            now = self.clock()
            if now - t0 > CLOSE_TIMEOUT:
                self._log(account, f"terminál PID {pid} sa do {CLOSE_TIMEOUT:.0f} s nezavrel — zabíjam natvrdo")
                self.processes.close(pid, force=True)
                self.sleep(2.0)
                break
            if now - last >= CLOSE_RETRY:
                # terminál, ktorý ešte len štartuje (bez okna), prvý WM_CLOSE nevidí — poslať znova
                self.processes.close(pid)
                last = now
            self.sleep(1.0)

    def _start(self, account: Account, exe: Path, ini: Path, portable: bool) -> int:
        cmd = [str(exe), f"/config:{ini.resolve()}"] + (["/portable"] if portable else [])
        pid = self.processes.start(cmd, exe.parent)
        started = self.clock()
        (self.account_dir(account) / "terminal.pid").write_text(
            json.dumps({"pid": pid, "started": started, "exe": str(exe), "ini": str(ini)}), encoding="utf-8")
        self._log(account, f"spustený {' '.join(cmd)} -> PID {pid}")
        return pid

    def ensure_instance(self, account: Account, deployments: list[Deployment]) -> None:
        exe, data_dir, portable = self.terminal_for(account)
        charts = self._charts(account, deployments)
        key = self._charts_key(charts)
        ident = self.spool_account(account)
        manifest = self._manifest(account)
        # identita účtu je v id inštancií aj v ini (Login/Server) — iný login = iný terminál, nie ten istý
        # s tými istými grafmi; starý manifest bez `account` sa berie ako zhodný
        same = (manifest is not None and manifest.get("key") == key and manifest.get("account", ident) == ident
                and self._profile_matches(data_dir, charts))
        pid = self._running_pid(account)
        if pid is not None and same:
            self._scrub_password(account)
            self._drop_removed_controls(account, None, charts)   # grafy z manifestu bežia ďalej; len odložené
            return
        if not charts and pid is None and same:
            self._drop_removed_controls(account, manifest, charts)
            return   # nič nemá bežať a nič nebeží
        # zmena množiny grafov alebo terminál nebeží: (re)štart
        foreign = [] if pid is not None else [p for p in self.processes.find(exe) if p]
        for p in ([pid] if pid is not None else foreign):
            self._close(account, p)
        if not same:
            self.write_chart_profile(data_dir, charts)
            self._log(account, "profil grafov `tradebot`: " + (", ".join(f"{c['symbol']} {c['tf']}m {c['expert']}({c['profile']})"
                                                                     for c in charts) or "bez grafov"))
        # terminál je zavretý: control súbory grafov, ktoré už nebudú, smú preč; tie, čo budú, musia existovať
        self._drop_removed_controls(account, manifest, charts)
        d = self.account_dir(account)
        d.mkdir(parents=True, exist_ok=True)
        (d / "charts.json").write_text(json.dumps({"key": key, "account": ident, "charts": charts,
                                                   "profile_dir": str(self.profile_dir(data_dir)),
                                                   "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
        if not charts:
            self._log(account, "žiadne aktívne nasadenie — terminál sa nespúšťa")
            return
        self._ensure_controls(account, deployments)
        ini = self._write_ini(account, with_password=True)
        self._start(account, exe, ini, portable)

    def _drop_removed_controls(self, account: Account, manifest: dict[str, Any] | None, charts: list[dict[str, Any]]) -> None:
        """Zmaže control súbory inštancií, ktoré už nemajú graf: tie z minulého manifestu (`manifest`, len
        keď je terminál zavretý — inak `None`) a tie, čo odložil `remove_instance`. Súbor by inak ostal ako
        stará správa pre EA, keby sa inštancia niekedy vrátila. Volá sa až po zavretí terminálu s tými grafmi."""
        from tradebot.adapters.mt5.__main__ import control_dir

        zostavaju = {c["instance"] for c in charts}
        kandidati: set[str] = set(self._pending_remove.pop(account.id, set()))
        for old in (manifest or {}).get("charts") or []:
            inst = old.get("instance") if isinstance(old, dict) else None
            if inst:
                kandidati.add(inst)
        for inst in sorted(kandidati - zostavaju):
            path = control_dir(self.common()) / f"{inst}.json"
            if path.exists():
                path.unlink()
                self._log(account, f"control súbor {inst} zmazaný (graf už v profile nie je)")

    def _scrub_password(self, account: Account) -> None:
        """Heslo je v ini len na prihlásenie — po `PASSWORD_TTL` s od štartu sa ini prepíše bez neho."""
        info = self._pid_info(account)
        ini = self.account_dir(account) / "start.ini"
        try:
            if "Password=" not in ini.read_text(encoding="utf-8"):
                return
        except OSError:
            return
        if self.clock() - float(info.get("started") or 0) >= PASSWORD_TTL:
            self._write_ini(account, with_password=False)
            self._log(account, "heslo z start.ini zmazané (terminál je prihlásený)")

    def status(self, account: Account) -> dict[str, Any]:
        info = self._pid_info(account)
        manifest = self._manifest(account) or {}
        pid = self._running_pid(account)
        out: dict[str, Any] = {
            "platform": self.platform, "running": pid is not None, "pid": pid,
            "started": datetime.fromtimestamp(float(info["started"]), tz=timezone.utc).isoformat(timespec="seconds")
            if info.get("started") else None,
            "ini": str(self.account_dir(account) / "start.ini"), "log": str(self.account_dir(account) / "driver.log"),
            "charts": [{k: c.get(k) for k in ("deployment", "instance", "symbol", "tf", "expert", "profile", "magic")}
                       for c in manifest.get("charts") or []],
            "profile_dir": manifest.get("profile_dir"),
        }
        try:
            exe, data_dir, portable = self.terminal_for(account) if (account.terminal or not account.portable) else (None, None, True)
            out.update(exe=str(exe) if exe else None, data_dir=str(data_dir) if data_dir else None, portable=portable)
        except Exception as exc:  # noqa: BLE001 - stav nesmie padnúť
            out["error"] = str(exc)
        out["installed"] = self.installed_version()
        return out

    # -- kód platformy (docs/LIVE.md, fáza 2c) --------------------------------- #

    def installed_version(self) -> str | None:
        """Commit z `Common\\Files\\TradeBot\\installed.json` (píše ho `install`), alebo `None`."""
        from tradebot.adapters.mt5.__main__ import read_installed

        try:
            data = read_installed(self.common())
        except Exception:  # noqa: BLE001
            return None
        return str((data or {}).get("version") or "") or None

    def _install_targets(self, accounts: list[Account]) -> list[tuple[Account | None, Path, Path, bool]]:
        """Kam sa kód inštaluje: dátový adresár každého terminálu účtov (portable kópia len keď už existuje)
        a nainštalovaný terminál stroja (aj bez účtov — `install` naň ukazuje aj CLI)."""
        out: list[tuple[Account | None, Path, Path, bool]] = []
        seen: set[str] = set()
        for acc in accounts:
            if acc.portable and not acc.terminal.strip() and not (self.account_dir(acc) / "terminal" / EXE_NAME).is_file():
                continue   # portable kópia ešte nevznikla — vznikne až pri `ensure_instance` už z nového kódu
            try:
                exe, data_dir, portable = self.terminal_for(acc)
            except ValueError as exc:
                self._log(acc, f"kód: terminál účtu sa nenašiel: {exc}")
                continue
            key = os.path.normcase(str(data_dir))
            if key not in seen:
                seen.add(key)
                out.append((acc, exe, data_dir, portable))
        exe = self._installed_exe()
        if exe is not None:
            try:
                data_dir = self._data_dir_for(exe)
                if os.path.normcase(str(data_dir)) not in seen:
                    out.append((None, exe, data_dir, False))
            except ValueError:
                pass
        return out

    def install_code(self, version: str, accounts: list[Account]) -> dict[str, Any]:
        """Slušne zavrie terminály účtov (aj cudzie z toho istého `exe` — DLL je zamknutá, kým EA beží), potom
        `install` z `tradebot.adapters.mt5` do každého dátového adresára (DLL, includy, šablóny, presety,
        profily, preklad MetaEditorom) a marker `installed.json` v `Common\\Files\\TradeBot`. Terminály znova
        spustí `ensure_instance` v ďalšom kole reconcilera (pid neexistuje → štart s ini)."""
        from tradebot.adapters.mt5.__main__ import install, write_installed

        targets = self._install_targets(accounts)
        if not targets:
            raise ValueError("nenašiel sa žiadny terminál MT5, do ktorého by sa kód nainštaloval")
        closed: list[int] = []
        for acc in accounts:
            pid = self._running_pid(acc)
            if pid is not None:
                self._close(acc, pid)
                closed.append(pid)
        for acc, exe, _data_dir, _portable in targets:
            for p in self.processes.find(exe):
                if p and p not in closed:
                    self._close(acc or Account(id="_", platform=self.platform), p)
                    closed.append(p)
        installed: list[dict[str, Any]] = []
        for acc, exe, data_dir, portable in targets:
            mql5 = data_dir / "MQL5"
            say = (lambda t, a=acc: self._log(a, "kód: " + t.replace("\n", " | "))) if acc is not None \
                else (lambda t: log.info("mt5 driver: kód: %s", t.replace("\n", " | ")))
            r = install(mql5, [], say=say, common=self.common())
            installed.append({"account": acc.id if acc else None, "mql5": str(mql5), "portable": portable,
                              "compiled": r.get("compiled")})
        marker = write_installed(self.common(), version, by="hub")
        for acc in accounts:
            self._log(acc, f"kód {version} nainštalovaný ({len(installed)} terminálov), terminál spustí ďalšie kolo")
        return {"closed": closed, "installed_to": installed, "marker": marker}


DRIVER = Mt5Driver()
