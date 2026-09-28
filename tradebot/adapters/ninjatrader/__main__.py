"""Inštalácia a kontrola adaptéra NinjaTrader 8.

    python -m tradebot.adapters.ninjatrader check       # preloží adaptér proti DLL NinjaTradera (nič nekopíruje)
    python -m tradebot.adapters.ninjatrader install [--compile]   # skopíruje jadro, adaptér, AddOn, šablóny a profily (a skúsi preklad bez človeka)
    python -m tradebot.adapters.ninjatrader compile     # len preklad bez človeka: MSBuild, potom F5 v NinjaScript Editore (pywinauto)
    python -m tradebot.adapters.ninjatrader profiles    # len znova vyexportuje profily
    python -m tradebot.adapters.ninjatrader control list                                   # control súbory a inštancie spoolu
    python -m tradebot.adapters.ninjatrader control <inštancia> [--mode M] [--profile P]   # zapíše control súbor

`install` kopíruje **zdrojáky** (nie DLL) do `Documents\\NinjaTrader 8\\bin\\Custom`: NinjaTrader si
ich preloží sám spolu s ostatným NinjaScriptom (NinjaScript Editor → F5), takže netreba pridávať
referenciu na DLL a po zmene jadra stačí `install` zopakovať. Profily idú ako úplné configy do
`Documents\\NinjaTrader 8\\TradeBot\\profiles\\<stratégia>\\` a v parametri stratégie „Profil" sa
zadávajú menom.

`install` zapíše aj `Documents\\NinjaTrader 8\\TradeBot\\installed.json` (`version` = commit klonu, `compiled`)
— podľa neho hub a webapp vedia, na akom kóde platforma stojí (docs/LIVE.md, fáza 2c). Preklad bez človeka
(`compile`, `install --compile`, driver agenta): `NinjaTrader.Custom.csproj` je SDK-style projekt (`Sdk=Microsoft.NET.Sdk`,
C# 13, NuGet), ktorý MSBuild z .NET Frameworku nenačíta (MSB4041) — skúsi sa, a keď nevyrobí `bin\\Custom\\NinjaTrader.Custom.dll`,
pošle sa **F5 do okna NinjaScript Editora** bežiaceho NinjaTradera (pywinauto, UIA); úspech = DLL sa zmenila
a AddOn zapísal novú generáciu do `TradeBot\\logs\\addon_*.txt`. NinjaTrader musí bežať (prihlásený človekom).

`control` píše `Documents\\NinjaTrader 8\\TradeBot\\control\\<inštancia>.json` (docs/LIVE.md, fáza 2)
atomicky; bez `--mode` ostáva mode z existujúceho súboru (inak `enabled`), bez `--profile` ostáva
profil. Inštancia je názov adresára spoolu (`ninjatrader_Sim101_MNQ-12-26_3m_ibsnet`) alebo `addon`
pre sondu `TradeBotLiveAddOn`.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tradebot.adapters.csharp.build import BuildError, ensure_built, find_compiler
from tradebot.core.config import load_profile
from tradebot.core.paths import CSHARP_DIR, CSHARP_DLL, NINJATRADER_DIR
from tradebot.core.version import repo_version
from tradebot.strategies import STRATEGIES


class InstallError(RuntimeError):
    """Inštalácia alebo preklad zlyhali (CLI z toho spraví `SystemExit`, driver `status: error`)."""


ADAPTER_DIR = Path(__file__).resolve().parent
#: Adaptér (NinjaScript Strategy) — ide do `bin\\Custom\\Strategies`.
ADAPTER_FILE = ADAPTER_DIR / "TradeBotStrategy.cs"
#: AddOn (štartuje s NinjaTraderom, sonda behu bez človeka) — ide do `bin\\Custom\\AddOns\\TradeBot`.
ADDON_FILE = ADAPTER_DIR / "TradeBotLiveAddOn.cs"
#: Všetky zdrojáky AddOnu (supervízor + jedna inštancia enginu).
ADDON_FILES = (ADDON_FILE, ADAPTER_DIR / "TradeBotLiveInstance.cs")
#: Zdrojáky C# jadra, ktoré idú do NinjaTradera (hostiteľ pre stdio most nie).
CORE_DIRS = ("TradeBot.Core", "TradeBot.Strategies")
CONTROL_MODES = ("enabled", "paused", "flatten")
#: Šablóny, ktoré `install` z NinjaTradera odstráni: IBSNinja/ORBNinja sa 25. 9. 2026 premenovali na IBSNet/ORBNet.
STALE_TEMPLATES = ("IBSNinja.cs", "ORBNinja.cs")


def find_nt_user_dir(override: str | None = None) -> Path | None:
    """`Documents\\NinjaTrader 8` (`--nt-dir`, `TRADEBOT_NT_DIR`), alebo `None`, keď tam NinjaTrader
    nie je — nič nevyhadzuje, nech sa dá použiť aj tam, kde platforma len môže byť (live spool)."""
    try:
        raw = override or os.environ.get("TRADEBOT_NT_DIR")
        path = Path(raw) if raw else Path.home() / "Documents" / "NinjaTrader 8"
        return path if (path / "bin" / "Custom").is_dir() else None
    except (OSError, RuntimeError):
        return None


def nt_user_dir(override: str | None = None) -> Path:
    """`Documents\\NinjaTrader 8` — dá sa vnútiť (`--nt-dir`, `TRADEBOT_NT_DIR`), keď sú Dokumenty inde."""
    path = find_nt_user_dir(override)
    if path is None:
        raw = override or os.environ.get("TRADEBOT_NT_DIR")
        hladane = Path(raw) if raw else Path.home() / "Documents" / "NinjaTrader 8"
        raise SystemExit(f"NinjaTrader 8 sa nenašiel v {hladane} (chýba bin\\Custom); zadaj --nt-dir")
    return path


def nt_install_dir() -> Path:
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if root and (Path(root) / "NinjaTrader 8" / "bin" / "NinjaTrader.Core.dll").exists():
            return Path(root) / "NinjaTrader 8" / "bin"
    raise InstallError("inštalácia NinjaTrader 8 sa nenašla (Program Files\\NinjaTrader 8)")


def csharp_strategies():
    """Stratégie, ktoré adaptér vie spustiť — tie, čo majú jadro v C#."""
    return [s for s in STRATEGIES.values() if s.csharp_dir is not None]


def check_sources() -> list[Path]:
    """Všetko, čo NinjaTrader po `install` prekladá: jadro, adaptér, AddOn, šablóny."""
    core = [f for d in CORE_DIRS for f in sorted((CSHARP_DIR / d).rglob("*.cs"))]
    templates = sorted(NINJATRADER_DIR.glob("*.cs"))
    return [*core, ADAPTER_FILE, *ADDON_FILES, *templates]


def check(nt_dir: Path, *, say: Callable[[str], None] = print) -> None:
    """Preloží adaptér a šablóny proti skutočným DLL NinjaTradera — chyba API sa ukáže tu, nie v grafe."""
    ensure_built()
    nt_bin = nt_install_dir()
    wpf = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "WPF"
    refs = [nt_bin / "NinjaTrader.Core.dll", nt_bin / "NinjaTrader.Gui.dll",
            nt_dir / "bin" / "Custom" / "NinjaTrader.Custom.dll",
            wpf / "WindowsBase.dll", wpf / "PresentationCore.dll", wpf / "PresentationFramework.dll"]
    # Jadro ide do prekladu ako ZDROJÁKY, nie ako DLL — presne tak ho prekladá NinjaTrader. A po
    # `install` už `NinjaTrader.Custom.dll` tie isté typy obsahuje: typ definovaný v prekladanej
    # assembly má prednosť (len varovanie CS0436), kým dva referencované by bola chyba.
    files = check_sources()
    templates = sorted(NINJATRADER_DIR.glob("*.cs"))
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [*find_compiler(), "-nologo", "-codepage:65001", "-nowarn:0436", "-target:library",
               f"-out:{Path(tmp) / 'nt_check.dll'}",
               *[f"-r:{r}" for r in refs], "-r:System.Xaml.dll", "-r:System.ComponentModel.DataAnnotations.dll",
               *[str(f) for f in files]]
        done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise InstallError(f"adaptér sa proti NinjaTraderu nepreložil:\n{done.stdout}{done.stderr}")
    say(f"OK: jadro, adaptér, AddOn a {len(templates)} šablón sa preložilo proti {nt_bin}")


def export_profiles(nt_dir: Path, extra: list[str]) -> int:
    """Profily ako úplné configy (`to_dict()` + `_instrument`) — C# číta ten istý tvar ako Python."""
    count = 0
    for spec in csharp_strategies():
        out_dir = nt_dir / "TradeBot" / "profiles"
        out_dir.mkdir(parents=True, exist_ok=True)
        sources = [*sorted(spec.profile_dir.glob("*.json")), *[Path(p) for p in extra]]
        for src in sources:
            raw = json.loads(src.read_text(encoding="utf-8"))
            if raw.get("_strategy", spec.key) != spec.key:
                continue  # `--profile` patrí inej C# stratégii

            cfg, _inst = load_profile(src, strategy=spec.key)
            data = {"_strategy": spec.key, "_instrument": raw.get("_instrument"), "_source": str(src), **cfg.to_dict()}
            (out_dir / src.name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            count += 1
    return count


# --------------------------------------------------------------------------- #
# marker nainštalovaného kódu (docs/LIVE.md, fáza 2c): TradeBot/installed.json
# --------------------------------------------------------------------------- #


def installed_marker(nt_dir: Path) -> Path:
    return nt_dir / "TradeBot" / "installed.json"


def read_installed(nt_dir: Path) -> dict | None:
    """`{"version", "installed", "by", "platform", "compiled"}` z markera, alebo `None`."""
    try:
        data = json.loads(installed_marker(nt_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("version") else None


def write_installed(nt_dir: Path, version: str, by: str | None = None, compiled: bool | None = None) -> dict:
    """Zapíše marker atomicky; `compiled=False` = zdrojáky sú na disku, ale NinjaTrader ich ešte nepreložil
    (`installed_version` drivera taký marker nepočíta ako nainštalovaný kód)."""
    data: dict[str, Any] = {"platform": "ninjatrader", "version": str(version or ""),
                            "installed": datetime.now(timezone.utc).isoformat(timespec="seconds"), "by": by or _whoami()}
    if compiled is not None:
        data["compiled"] = bool(compiled)
    path = installed_marker(nt_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".installed.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return data


def install(nt_dir: Path, extra_profiles: list[str], *, say: Callable[[str], None] = print,
            version: str | None = None, by: str | None = None, compiled: bool | None = None) -> dict:
    """Skopíruje jadro, AddOn, adaptér, šablóny a profily do NinjaTradera. Chyba = `InstallError`/`BuildError`
    (nie `SystemExit`), aby to vedel volať aj driver agenta. S `version` zapíše marker `installed.json`
    (`compiled` hovorí, či zdrojáky niekto aj preložil). Vráti, čo urobil."""
    check(nt_dir, say=say)
    custom = nt_dir / "bin" / "Custom"
    target = custom / "AddOns" / "TradeBot"
    if target.exists():
        shutil.rmtree(target)  # vlastný adresár adaptéra — zmazané zdrojáky jadra nesmú v NinjaTraderi ostať
    for d in CORE_DIRS:
        shutil.copytree(CSHARP_DIR / d, target / d)
    for f in ADDON_FILES:
        shutil.copy2(f, target / f.name)
    shutil.copy2(ADAPTER_FILE, custom / "Strategies" / ADAPTER_FILE.name)
    for stale in STALE_TEMPLATES:   # šablóny spred premenovania by sa preložili, ale ich kľúč už engine nepozná
        (custom / "Strategies" / stale).unlink(missing_ok=True)
    templates = sorted(NINJATRADER_DIR.glob("*.cs"))
    for t in templates:
        shutil.copy2(t, custom / "Strategies" / t.name)
    n = export_profiles(nt_dir, extra_profiles)
    say(f"OK: jadro + AddOn ({ADDON_FILE.stem}) -> {target}\n"
        f"OK: adaptér + šablóny ({', '.join(t.stem for t in templates)}) -> {custom / 'Strategies'}\n"
        f"OK: {n} profilov -> {nt_dir / 'TradeBot' / 'profiles'}\n"
        "Teraz v NinjaTraderi: New > NinjaScript Editor > F5 (preklad) — alebo `compile` / driver agenta.")
    out: dict[str, Any] = {"target": str(target), "templates": [t.stem for t in templates], "profiles": n}
    if version:
        out["marker"] = write_installed(nt_dir, version, by, compiled)
    return out


# --------------------------------------------------------------------------- #
# preklad bez človeka (docs/LIVE.md fáza 2c, docs/NINJATRADER.md)
# --------------------------------------------------------------------------- #

CUSTOM_DLL = ("bin", "Custom", "NinjaTrader.Custom.dll")
CUSTOM_CSPROJ = ("bin", "Custom", "NinjaTrader.Custom.csproj")
#: Koľko sekúnd čakať po F5, kým sa `NinjaTrader.Custom.dll` zmení a AddOn ohlási novú generáciu.
COMPILE_TIMEOUT = 90.0
GENERATION_MARK = "start generacia"


def msbuild_path() -> Path | None:
    """`MSBuild.exe` z .NET Frameworku (`TRADEBOT_MSBUILD` ho prebije), alebo `None`."""
    raw = os.environ.get("TRADEBOT_MSBUILD")
    if raw:
        return Path(raw) if Path(raw).is_file() else None
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for fw in ("Framework64", "Framework"):
        cand = windir / "Microsoft.NET" / fw / "v4.0.30319" / "MSBuild.exe"
        if cand.is_file():
            return cand
    return None


def custom_dll(nt_dir: Path) -> Path:
    return nt_dir.joinpath(*CUSTOM_DLL)


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def addon_generation(nt_dir: Path) -> tuple[str | None, str | None]:
    """`(názov logu, generácia)` najnovšieho `TradeBot\\logs\\addon_*.txt`, ktorý hlási `start generacia`."""
    logs = nt_dir / "TradeBot" / "logs"
    try:
        files = sorted(logs.glob("addon_*.txt"))
    except OSError:
        return None, None
    for f in reversed(files):
        try:
            head = f.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        i = head.find(GENERATION_MARK)
        if i >= 0:
            gen = head[i + len(GENERATION_MARK):].split(None, 1)
            return f.name, (gen[0] if gen else None)
    return None, None


def nt_compile_msbuild(nt_dir: Path, *, csproj: Path | None = None, timeout: float = 600.0,
                       run=subprocess.run) -> dict[str, Any]:
    """Pokus (i): MSBuild z .NET Frameworku na `NinjaTrader.Custom.csproj`. Úspech = DLL, ktorú NinjaTrader
    načítava (`bin\\Custom\\NinjaTrader.Custom.dll`), sa zmenila. Nikdy nevyhodí výnimku."""
    csproj = csproj or nt_dir.joinpath(*CUSTOM_CSPROJ)
    dll = custom_dll(nt_dir)
    out: dict[str, Any] = {"method": "msbuild", "ok": False, "csproj": str(csproj), "dll": str(dll)}
    exe = msbuild_path()
    if exe is None:
        out["error"] = "MSBuild.exe sa nenašiel (C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319; TRADEBOT_MSBUILD)"
        return out
    if not csproj.is_file():
        out["error"] = f"{csproj} nie je"
        return out
    before = _mtime(dll)
    try:
        done = run([str(exe), str(csproj), "-nologo", "-v:m", "-p:Configuration=Release", "-p:Platform=x64"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                   cwd=str(csproj.parent))
    except (OSError, subprocess.SubprocessError) as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    text = (done.stdout or "") + (done.stderr or "")
    out["returncode"] = done.returncode
    out["output"] = text.strip()[-1500:]
    if done.returncode != 0:
        out["error"] = "MSBuild zlyhal: " + text.strip()[-400:]
        return out
    after = _mtime(dll)
    if after is None or after == before:
        out["error"] = "MSBuild prešiel, ale DLL, ktorú NinjaTrader načítava, sa nezmenila (výstup ide inam)"
        return out
    out["ok"] = True
    return out


def nt_running_pid() -> int | None:
    """PID bežiaceho `NinjaTrader.exe` (Windows), inak `None`."""
    if sys.platform != "win32":
        return None
    try:
        text = subprocess.run(["tasklist", "/FI", "IMAGENAME eq NinjaTrader.exe", "/FO", "CSV", "/NH"],
                              capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in text.splitlines():
        parts = [x.strip('"') for x in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == "ninjatrader.exe":
            try:
                return int(parts[1])
            except ValueError:
                continue
    return None


def nt_compile_via_editor(nt_dir: Path, *, timeout: float = COMPILE_TIMEOUT, sleep=time.sleep,
                          clock=time.time, pid: int | None = None) -> dict[str, Any]:
    """Pokus (ii): F5 do okna **NinjaScript Editora** bežiaceho NinjaTradera cez pywinauto (UIA) — presne to,
    čo by stlačil človek. Keď editor nie je otvorený, skúsi ho otvoriť z Control Center (New > NinjaScript
    Editor). Úspech = `NinjaTrader.Custom.dll` sa zmenila; navyše sa čaká, kým AddOn zapíše novú generáciu
    (`start generacia` v novom `addon_*.txt`) — bez nej NT síce preložil, ale AddOn nenabehol.
    Nikdy nevyhodí výnimku. Overené 28. 9. 2026 (DLL aj nová generácia do 2 s)."""
    dll = custom_dll(nt_dir)
    out: dict[str, Any] = {"method": "editor", "ok": False, "dll": str(dll), "compiled": False, "generation": None}
    try:
        from pywinauto import Application  # type: ignore[import-not-found]
    except ImportError:
        out["error"] = "pywinauto nie je nainštalované (pip install pywinauto)"
        return out
    pid = pid or nt_running_pid()
    if pid is None:
        out["error"] = "NinjaTrader nebeží — preklad urobí až bežiaci NT (F5), zdrojáky sú nakopírované"
        return out
    log_before, gen_before = addon_generation(nt_dir)
    before = _mtime(dll)
    try:
        app = Application(backend="uia").connect(process=pid, timeout=20)
        win = app.window(title_re="NinjaScript Editor.*")
        if not win.exists(timeout=2):
            # otvoriť z Control Center: New > NinjaScript Editor (neoverené — v teste už editor bežal)
            cc = app.window(class_name="ControlCenter")
            cc.set_focus()
            cc.menu_select("New->NinjaScript Editor")
            win = app.window(title_re="NinjaScript Editor.*")
            win.wait("exists visible", timeout=30)
        win.set_focus()
        sleep(0.5)
        win.type_keys("{F5}", set_foreground=True)
    except Exception as exc:  # noqa: BLE001 - UI automatizácia: čokoľvek, hlási sa ako chyba
        out["error"] = f"F5 v NinjaScript Editore sa nepodarilo poslať: {type(exc).__name__}: {exc}"[:600]
        return out
    t0 = clock()
    while clock() - t0 < timeout:
        sleep(1.0)
        if not out["compiled"] and _mtime(dll) not in (None, before):
            out["compiled"] = True
            out["seconds"] = round(clock() - t0, 1)
        log_now, gen_now = addon_generation(nt_dir)
        if out["compiled"] and log_now and (log_now != log_before or gen_now != gen_before):
            out["generation"] = gen_now
            out["log"] = log_now
            out["ok"] = True
            return out
    if out["compiled"]:
        out["ok"] = True   # DLL nová; AddOn sa neozval (nie je nasadený? pozri logs) — preklad ale prešiel
        out["warning"] = "DLL preložená, ale AddOn novú generáciu neohlásil (žiadny nový addon_*.txt)"
    else:
        out["error"] = (f"po F5 sa {dll.name} do {timeout:.0f} s nezmenila — chyba prekladu? pozri NinjaScript Editor "
                        "(Log / Errors) v NinjaTraderi")
    return out


def nt_compile(nt_dir: Path, *, msbuild: Callable[[Path], dict[str, Any]] | None = None,
               editor: Callable[[Path], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Preklad bez človeka: najprv MSBuild (i), keď nevyrobí DLL, F5 v editore (ii). Vráti výsledok toho,
    čo prešlo (alebo posledného pokusu), s `attempts` pre všetky."""
    attempts: list[dict[str, Any]] = []
    for fn in ((msbuild or nt_compile_msbuild), (editor or nt_compile_via_editor)):
        r = fn(nt_dir)
        attempts.append(r)
        if r.get("ok"):
            break
    out = dict(attempts[-1])
    out["attempts"] = attempts
    return out


# --------------------------------------------------------------------------- #
# control súbor (docs/LIVE.md, fáza 2)
# --------------------------------------------------------------------------- #


def control_dir(nt_dir: Path) -> Path:
    return nt_dir / "TradeBot" / "control"


def read_control(nt_dir: Path, instance: str) -> dict | None:
    path = control_dir(nt_dir) / f"{instance}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_control(nt_dir: Path, instance: str, *, mode: str | None = None, profile: str | None = None,
                  by: str | None = None) -> dict:
    """Zapíše control súbor atomicky (tmp + `os.replace`), nezadané polia prevezme z existujúceho súboru.
    Adaptér číta podľa mtime, takže každý zápis je pre neho nová správa aj pri rovnakom obsahu."""
    if mode is not None and mode not in CONTROL_MODES:
        raise SystemExit(f"mode musí byť {'/'.join(CONTROL_MODES)}, nie {mode!r}")
    if "/" in instance or "\\" in instance or instance in ("", ".", ".."):
        raise SystemExit(f"neplatná inštancia {instance!r}")
    current = read_control(nt_dir, instance) or {}
    data = {
        "mode": mode if mode is not None else current.get("mode", "enabled"),
        "profile": profile if profile is not None else current.get("profile", ""),
        "updated": int(time.time() * 1000),
        "by": by or current.get("by") or _whoami(),
    }
    directory = control_dir(nt_dir)
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{instance}.", suffix=".json.tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False) + "\n")
        os.replace(tmp, directory / f"{instance}.json")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return data


def _whoami() -> str:
    try:
        return f"{getpass.getuser()}@{os.environ.get('COMPUTERNAME') or os.uname().nodename}"
    except Exception:  # noqa: BLE001 - len popis, nie logika
        return "cli"


def list_control(nt_dir: Path) -> list[dict]:
    """Inštancie zo spoolu a z control adresára (zjednotené), s obsahom control súboru, ak je."""
    names: set[str] = set()
    spool = nt_dir / "TradeBot" / "spool"
    if spool.is_dir():
        names.update(p.name for p in spool.iterdir() if p.is_dir())
    if control_dir(nt_dir).is_dir():
        names.update(p.stem for p in control_dir(nt_dir).glob("*.json"))
    return [{"instance": n, "control": read_control(nt_dir, n), "spool": (spool / n).is_dir()} for n in sorted(names)]


def cmd_control(nt_dir: Path, args: argparse.Namespace) -> int:
    if not args.instance:
        raise SystemExit("control: zadaj inštanciu alebo `list`")
    if args.instance == "list":
        rows = list_control(nt_dir)
        if not rows:
            print(f"žiadne inštancie (spool ani control v {nt_dir / 'TradeBot'})")
        for r in rows:
            c = r["control"]
            stav = f"mode={c.get('mode')} profile={c.get('profile') or '-'} by={c.get('by') or '-'}" if c else "bez control súboru (= enabled)"
            print(f"{r['instance']:<55} {'spool' if r['spool'] else '     '}  {stav}")
        return 0
    profile = args.profile[-1] if args.profile else None
    if args.mode is None and profile is None:
        current = read_control(nt_dir, args.instance)
        print(json.dumps(current, ensure_ascii=False) if current else f"{args.instance}: bez control súboru (= enabled, profil z parametrov)")
        return 0
    data = write_control(nt_dir, args.instance, mode=args.mode, profile=profile, by=args.by)
    print(f"OK: {control_dir(nt_dir) / (args.instance + '.json')}\n{json.dumps(data, ensure_ascii=False)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("check", "install", "profiles", "control", "compile"))
    ap.add_argument("--compile", action="store_true", help="install: po nakopírovaní skúsiť preklad bez človeka (MSBuild, potom F5 v editore)")
    ap.add_argument("instance", nargs="?", help="control: inštancia (adresár spoolu, `addon`) alebo `list`")
    ap.add_argument("--nt-dir", help="adresár `Documents\\NinjaTrader 8`, keď nie je na obvyklom mieste")
    ap.add_argument("--profile", action="append", default=[],
                    help="install/profiles: ďalší profil (cesta k JSON) na export; control: profil pre adaptér")
    ap.add_argument("--mode", choices=CONTROL_MODES, help="control: enabled / paused / flatten")
    ap.add_argument("--by", help="control: kto zmenu zadal (predvolene používateľ@stroj)")
    args = ap.parse_args(argv)
    if sys.platform != "win32" and args.command != "control":
        raise SystemExit("NinjaTrader 8 beží len na Windows")
    nt_dir = nt_user_dir(args.nt_dir)
    try:
        if args.command == "check":
            check(nt_dir)
        elif args.command == "install":
            version = repo_version() or None
            install(nt_dir, args.profile, version=version, compiled=False if version else None)
            if args.compile:
                return cmd_compile(nt_dir, version)
        elif args.command == "compile":
            return cmd_compile(nt_dir, repo_version() or None)
        elif args.command == "control":
            return cmd_control(nt_dir, args)
        else:
            print(f"OK: {export_profiles(nt_dir, args.profile)} profilov")
    except (BuildError, InstallError) as exc:
        raise SystemExit(str(exc))
    return 0


def cmd_compile(nt_dir: Path, version: str | None) -> int:
    r = nt_compile(nt_dir)
    for a in r.get("attempts") or []:
        print(f"{a.get('method')}: {'OK' if a.get('ok') else 'nie'}"
              + (f" — {a.get('error')}" if a.get("error") else "")
              + (f" (generácia {a.get('generation')}, {a.get('seconds')} s)" if a.get("generation") else ""))
    if version:
        write_installed(nt_dir, version, compiled=bool(r.get("ok")))
    if not r.get("ok"):
        print("Preklad bez človeka neprešiel — v NinjaTraderi: New > NinjaScript Editor > F5.")
        return 1
    if r.get("warning"):
        print(f"varovanie: {r['warning']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
