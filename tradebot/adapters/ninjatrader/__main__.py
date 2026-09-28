"""Inštalácia a kontrola adaptéra NinjaTrader 8.

    python -m tradebot.adapters.ninjatrader check       # preloží adaptér proti DLL NinjaTradera (nič nekopíruje)
    python -m tradebot.adapters.ninjatrader install     # skopíruje jadro, adaptér, AddOn, šablóny a profily
    python -m tradebot.adapters.ninjatrader profiles    # len znova vyexportuje profily
    python -m tradebot.adapters.ninjatrader control list                                   # control súbory a inštancie spoolu
    python -m tradebot.adapters.ninjatrader control <inštancia> [--mode M] [--profile P]   # zapíše control súbor

`install` kopíruje **zdrojáky** (nie DLL) do `Documents\\NinjaTrader 8\\bin\\Custom`: NinjaTrader si
ich preloží sám spolu s ostatným NinjaScriptom (NinjaScript Editor → F5), takže netreba pridávať
referenciu na DLL a po zmene jadra stačí `install` zopakovať. Profily idú ako úplné configy do
`Documents\\NinjaTrader 8\\TradeBot\\profiles\\<stratégia>\\` a v parametri stratégie „Profil" sa
zadávajú menom.

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
from pathlib import Path

from tradebot.adapters.csharp.build import BuildError, ensure_built, find_compiler
from tradebot.core.config import load_profile
from tradebot.core.paths import CSHARP_DIR, CSHARP_DLL, NINJATRADER_DIR
from tradebot.strategies import STRATEGIES

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
    raise SystemExit("inštalácia NinjaTrader 8 sa nenašla (Program Files\\NinjaTrader 8)")


def csharp_strategies():
    """Stratégie, ktoré adaptér vie spustiť — tie, čo majú jadro v C#."""
    return [s for s in STRATEGIES.values() if s.csharp_dir is not None]


def check_sources() -> list[Path]:
    """Všetko, čo NinjaTrader po `install` prekladá: jadro, adaptér, AddOn, šablóny."""
    core = [f for d in CORE_DIRS for f in sorted((CSHARP_DIR / d).rglob("*.cs"))]
    templates = sorted(NINJATRADER_DIR.glob("*.cs"))
    return [*core, ADAPTER_FILE, *ADDON_FILES, *templates]


def check(nt_dir: Path) -> None:
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
        raise SystemExit(f"adaptér sa proti NinjaTraderu nepreložil:\n{done.stdout}{done.stderr}")
    print(f"OK: jadro, adaptér, AddOn a {len(templates)} šablón sa preložilo proti {nt_bin}")


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


def install(nt_dir: Path, extra_profiles: list[str]) -> None:
    check(nt_dir)
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
    print(f"OK: jadro + AddOn ({ADDON_FILE.stem}) -> {target}\n"
          f"OK: adaptér + šablóny ({', '.join(t.stem for t in templates)}) -> {custom / 'Strategies'}\n"
          f"OK: {n} profilov -> {nt_dir / 'TradeBot' / 'profiles'}\n"
          "Teraz v NinjaTraderi: New > NinjaScript Editor > F5 (preklad).")


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
    ap.add_argument("command", choices=("check", "install", "profiles", "control"))
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
            install(nt_dir, args.profile)
        elif args.command == "control":
            return cmd_control(nt_dir, args)
        else:
            print(f"OK: {export_profiles(nt_dir, args.profile)} profilov")
    except BuildError as exc:
        raise SystemExit(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
