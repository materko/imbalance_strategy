"""Inštalácia a kontrola adaptéra NinjaTrader 8.

    python -m tradebot.adapters.ninjatrader check       # preloží adaptér proti DLL NinjaTradera (nič nekopíruje)
    python -m tradebot.adapters.ninjatrader install     # skopíruje jadro, adaptér, šablóny a profily
    python -m tradebot.adapters.ninjatrader profiles    # len znova vyexportuje profily

`install` kopíruje **zdrojáky** (nie DLL) do `Documents\\NinjaTrader 8\\bin\\Custom`: NinjaTrader si
ich preloží sám spolu s ostatným NinjaScriptom (NinjaScript Editor → F5), takže netreba pridávať
referenciu na DLL a po zmene jadra stačí `install` zopakovať. Profily idú ako úplné configy do
`Documents\\NinjaTrader 8\\TradeBot\\profiles\\<stratégia>\\` a v parametri stratégie „Profil" sa
zadávajú menom.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tradebot.adapters.csharp.build import BuildError, ensure_built, find_compiler
from tradebot.core.config import load_profile
from tradebot.core.paths import CSHARP_DIR, CSHARP_DLL, NINJATRADER_DIR
from tradebot.strategies import STRATEGIES

ADAPTER_DIR = Path(__file__).resolve().parent
#: Zdrojáky C# jadra, ktoré idú do NinjaTradera (hostiteľ pre stdio most nie).
CORE_DIRS = ("TradeBot.Core", "TradeBot.Strategies")


def nt_user_dir(override: str | None = None) -> Path:
    """`Documents\\NinjaTrader 8` — dá sa vnútiť (`--nt-dir`, `TRADEBOT_NT_DIR`), keď sú Dokumenty inde."""
    raw = override or os.environ.get("TRADEBOT_NT_DIR")
    path = Path(raw) if raw else Path.home() / "Documents" / "NinjaTrader 8"
    if not (path / "bin" / "Custom").is_dir():
        raise SystemExit(f"NinjaTrader 8 sa nenašiel v {path} (chýba bin\\Custom); zadaj --nt-dir")
    return path


def nt_install_dir() -> Path:
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if root and (Path(root) / "NinjaTrader 8" / "bin" / "NinjaTrader.Core.dll").exists():
            return Path(root) / "NinjaTrader 8" / "bin"
    raise SystemExit("inštalácia NinjaTrader 8 sa nenašla (Program Files\\NinjaTrader 8)")


def csharp_strategies():
    """Stratégie, ktoré adaptér vie spustiť — tie, čo majú jadro v C#."""
    return [s for s in STRATEGIES.values() if s.csharp_dir is not None]


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
    core = [f for d in CORE_DIRS for f in sorted((CSHARP_DIR / d).rglob("*.cs"))]
    templates = sorted(NINJATRADER_DIR.glob("*.cs"))
    files = [*core, ADAPTER_DIR / "TradeBotStrategy.cs", *templates]
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [*find_compiler(), "-nologo", "-codepage:65001", "-nowarn:0436", "-target:library",
               f"-out:{Path(tmp) / 'nt_check.dll'}",
               *[f"-r:{r}" for r in refs], "-r:System.Xaml.dll", "-r:System.ComponentModel.DataAnnotations.dll",
               *[str(f) for f in files]]
        done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"adaptér sa proti NinjaTraderu nepreložil:\n{done.stdout}{done.stderr}")
    print(f"OK: jadro, adaptér a {len(templates)} šablón sa preložilo proti {nt_bin}")


def export_profiles(nt_dir: Path, extra: list[str]) -> int:
    """Profily ako úplné configy (`to_dict()` + `_instrument`) — C# číta ten istý tvar ako Python."""
    count = 0
    for spec in csharp_strategies():
        out_dir = nt_dir / "TradeBot" / "profiles"
        out_dir.mkdir(parents=True, exist_ok=True)
        sources = [*sorted(spec.profile_dir.glob("*.json")), *[Path(p) for p in extra]]
        for src in sources:
            raw = json.loads(src.read_text(encoding="utf-8"))
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
    shutil.copy2(ADAPTER_DIR / "TradeBotStrategy.cs", custom / "Strategies" / "TradeBotStrategy.cs")
    templates = sorted(NINJATRADER_DIR.glob("*.cs"))
    for t in templates:
        shutil.copy2(t, custom / "Strategies" / t.name)
    n = export_profiles(nt_dir, extra_profiles)
    print(f"OK: jadro -> {target}\nOK: adaptér + šablóny ({', '.join(t.stem for t in templates)}) -> {custom / 'Strategies'}\n"
          f"OK: {n} profilov -> {nt_dir / 'TradeBot' / 'profiles'}\n"
          "Teraz v NinjaTraderi: New > NinjaScript Editor > F5 (preklad).")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("check", "install", "profiles"))
    ap.add_argument("--nt-dir", help="adresár `Documents\\NinjaTrader 8`, keď nie je na obvyklom mieste")
    ap.add_argument("--profile", action="append", default=[], help="ďalší profil (cesta k JSON) na export")
    args = ap.parse_args(argv)
    if sys.platform != "win32":
        raise SystemExit("NinjaTrader 8 beží len na Windows")
    nt_dir = nt_user_dir(args.nt_dir)
    try:
        if args.command == "check":
            check(nt_dir)
        elif args.command == "install":
            install(nt_dir, args.profile)
        else:
            print(f"OK: {export_profiles(nt_dir, args.profile)} profilov")
    except BuildError as exc:
        raise SystemExit(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
