"""Inštalácia adaptéra MetaTrader 5.

    python -m tradebot.adapters.mt5 install [--mt5-dir DIR] [--profile cesta.json ...]
    python -m tradebot.adapters.mt5 check                   # len preloží nainštalované EA a skripty MetaEditorom
    python -m tradebot.adapters.mt5 profiles                # len znova vyexportuje profily
    python -m tradebot.adapters.mt5 where                   # ukáže, ktoré dátové adresáre MT5 našiel
    python -m tradebot.adapters.mt5 csv [--instrument mnq_databento --from … --to …]   # 1m sviečky zo skladu -> Files\TradeBot\import
    python -m tradebot.adapters.mt5 run deploy/mt5/ini/import_mnq.ini        # spustí terminál so štartovacím ini a počká na koniec
    python -m tradebot.adapters.mt5 run deploy/mt5/ini/tester_ibsnet_mnq.ini # beh v Strategy Testeri bez klikania (treba účet)

Beh bez klikania: `csv` -> `run import_mnq.ini` (skript `TradeBotImport` spraví Custom symbol `MNQ.TB`
z našich UTC barov a terminál zavrie) -> `run tester_ibsnet_mnq.ini` (`[Tester]` sekcia, po behu sa
terminál vypne; správa `TradeBot_IBSNet.htm` v dátovom adresári, export signálov v `Common\Files\TradeBot\logs`).
Strategy Tester odmietne beh bez účtu („account is not specified") — demo účet si tester založí sám
v termináli (File > Open an Account), raz.

`install` zostaví `TradeBot.dll` (`tradebot.adapters.csharp.build`) a skopíruje:

    TradeBot.dll                       -> <MQL5>/Libraries/            (.NET import; musí byť tu, nie vedľa EA)
    TradeBotEA.mqh, TradeBotJson.mqh, TradeBotDraw.mqh -> <MQL5>/Include/TradeBot/
    deploy/mt5/<Meno>.mq5              -> <MQL5>/Experts/TradeBot/
    TradeBotImport.mq5                 -> <MQL5>/Scripts/TradeBot/        (Custom symbol z CSV)
    presets/*.set                      -> <MQL5>/Presets/ (skripty), <MQL5>/Profiles/Tester/ (EA v testeri)
    profily ako úplné configy          -> Common/Files/TradeBot/profiles/<kľúč>/   (FILE_COMMON: vidí ich aj agent Strategy Testera)

`<MQL5>` je `%APPDATA%\\MetaQuotes\\Terminal\\<hash>\\MQL5`; keď je terminálov viac, zadaj `--mt5-dir`
(alebo `TRADEBOT_MT5_DIR`). Preklad EA robí MetaEditor: `install` ho po nakopírovaní spustí sám
(`metaeditor64.exe /compile`, cesta cez `TRADEBOT_METAEDITOR`, keď nie je v Program Files) —
`.ex5` sa v termináli objaví bez F7. MetaEditor číta .NET DLL len z `Libraries` terminálu, preto sa
mimo neho prekladať nedá. Na rozdiel od NinjaTradera ide jadro ako **DLL**, nie zdrojáky: po zmene
v `csharp/` stačí `install` (terminál drží DLL otvorenú, kým EA beží — najprv ho z grafu odstráň).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from tradebot.adapters.csharp.build import BuildError, ensure_built
from tradebot.core.config import load_profile
from tradebot.core.paths import CSHARP_DLL, MT5_DIR
from tradebot.strategies import STRATEGIES

ADAPTER_DIR = Path(__file__).resolve().parent
INCLUDES = ("TradeBotEA.mqh", "TradeBotJson.mqh", "TradeBotDraw.mqh")
SCRIPTS = ("TradeBotImport.mq5",)
#: `.set` pre skripty idú do Presets, pre EA v Strategy Testeri do Profiles/Tester
PRESETS = {"TradeBotImport.set": ("Presets",), "IBSNet_TB.set": ("Profiles", "Tester"),
           "IBSNet_chart.set": ("Presets",)}


def metaeditor() -> Path | None:
    """`metaeditor64.exe` — z `TRADEBOT_METAEDITOR` alebo z Program Files."""
    raw = os.environ.get("TRADEBOT_METAEDITOR")
    if raw:
        return Path(raw)
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if root:
            for found in Path(root).glob("*/metaeditor64.exe"):
                return found
    return None


def compile_experts(mql5: Path) -> list[str]:
    """Preloží šablóny v `<MQL5>/Experts/TradeBot` a skripty v `Scripts/TradeBot` MetaEditorom;
    vráti riadky s chybami a varovaniami."""
    editor = metaeditor()
    if editor is None:
        raise SystemExit("metaeditor64.exe sa nenašiel (Program Files, MetaTrader 5); cestu zadaj cez TRADEBOT_METAEDITOR")
    problems: list[str] = []
    sources = [*sorted((mql5 / "Experts" / "TradeBot").glob("*.mq5")), *sorted((mql5 / "Scripts" / "TradeBot").glob("*.mq5"))]
    for src in sources:
        log = src.with_suffix(".log")
        log.unlink(missing_ok=True)
        subprocess.run([str(editor), f"/compile:{src}", f"/log:{log}"], check=False)
        text = log.read_text(encoding="utf-16", errors="replace") if log.exists() else ""
        log.unlink(missing_ok=True)
        lines = [line.strip() for line in text.splitlines() if " error " in line or " warning " in line]
        if not src.with_suffix(".ex5").exists():
            lines.append(f"{src.name}: .ex5 nevznikol")
        problems.extend(f"{src.stem}: {line.split(str(mql5))[-1].lstrip(chr(92))}" for line in lines)
    return problems


def candidate_dirs() -> list[Path]:
    """Všetky `MQL5` adresáre nainštalovaných terminálov (`%APPDATA%\\MetaQuotes\\Terminal\\*\\MQL5`)."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []
    root = Path(appdata) / "MetaQuotes" / "Terminal"
    return sorted(p for p in root.glob("*/MQL5") if (p / "Experts").is_dir()) if root.is_dir() else []


def mt5_dir(override: str | None = None) -> Path:
    raw = override or os.environ.get("TRADEBOT_MT5_DIR")
    if raw:
        path = Path(raw)
        if path.name != "MQL5" and (path / "MQL5").is_dir():
            path = path / "MQL5"
        if not (path / "Experts").is_dir():
            raise SystemExit(f"{path} nevyzerá ako adresár MQL5 (chýba Experts)")
        return path
    found = candidate_dirs()
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit("MetaTrader 5 sa nenašiel v %APPDATA%\\MetaQuotes\\Terminal; zadaj --mt5-dir <…\\MQL5>")
    raise SystemExit("viac terminálov MT5:\n  " + "\n  ".join(str(p) for p in found) + "\nzadaj --mt5-dir")


def common_files(mql5: Path) -> Path:
    """`%APPDATA%/MetaQuotes/Terminal/Common/Files` — jediný adresár, ktorý vidí terminál aj agent Strategy
    Testera (ten má vlastné prázdne `MQL5/Files`). EA číta profily a píše export s `FILE_COMMON`."""
    raw = os.environ.get("TRADEBOT_MT5_COMMON")
    return Path(raw) if raw else mql5.parent.parent / "Common" / "Files"


def csharp_strategies():
    return [s for s in STRATEGIES.values() if s.csharp_dir is not None]


def export_profiles(mql5: Path, extra: list[str]) -> int:
    """Profily ako úplné configy (`to_dict()` + `_instrument`) — rovnaký tvar ako pre NinjaTrader."""
    count = 0
    for spec in csharp_strategies():
        out_dir = common_files(mql5) / "TradeBot" / "profiles" / spec.key
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


def install(mql5: Path, extra_profiles: list[str]) -> None:
    dll = ensure_built()
    (mql5 / "Libraries").mkdir(exist_ok=True)
    try:
        shutil.copy2(dll, mql5 / "Libraries" / CSHARP_DLL.name)
    except PermissionError:
        raise SystemExit("TradeBot.dll je zamknutá — odstráň EA z grafu (alebo zavri terminál) a spusti install znova")
    inc = mql5 / "Include" / "TradeBot"
    inc.mkdir(parents=True, exist_ok=True)
    for name in INCLUDES:
        shutil.copy2(ADAPTER_DIR / name, inc / name)
    experts = mql5 / "Experts" / "TradeBot"
    experts.mkdir(parents=True, exist_ok=True)
    templates = sorted(MT5_DIR.glob("*.mq5"))
    for t in templates:
        shutil.copy2(t, experts / t.name)
    scripts = mql5 / "Scripts" / "TradeBot"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in SCRIPTS:
        shutil.copy2(ADAPTER_DIR / name, scripts / name)
    for name, sub in PRESETS.items():
        mql5.joinpath(*sub).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ADAPTER_DIR / "presets" / name, mql5.joinpath(*sub) / name)
    (mql5 / "Files" / "TradeBot" / "import").mkdir(parents=True, exist_ok=True)
    (common_files(mql5) / "TradeBot" / "logs").mkdir(parents=True, exist_ok=True)
    n = export_profiles(mql5, extra_profiles)
    print(f"OK: jadro -> {mql5 / 'Libraries' / CSHARP_DLL.name}\nOK: adaptér -> {inc}\n"
          f"OK: šablóny ({', '.join(t.stem for t in templates)}) -> {experts}\n"
          f"OK: {n} profilov -> {common_files(mql5) / 'TradeBot' / 'profiles'}")
    check(mql5)
    print("V termináli povoľ Tools > Options > Expert Advisors > Allow DLL imports a EA vlož na minútový graf.")


def check(mql5: Path) -> None:
    """Preklad nainštalovaných EA MetaEditorom — chyba API sa ukáže tu, nie až v termináli."""
    problems = compile_experts(mql5)
    errors = [x for x in problems if " error " in x or ".ex5 nevznikol" in x]
    for x in problems:
        print(("CHYBA: " if x in errors else "varovanie: ") + x)
    if errors:
        raise SystemExit("EA sa v MetaEditore nepreložilo")
    hotove = sorted(f.stem for d in ("Experts", "Scripts") for f in (mql5 / d / "TradeBot").glob("*.ex5"))
    print(f"OK: MetaEditor preložil {', '.join(hotove)} -> {mql5 / 'Experts' / 'TradeBot'}, {mql5 / 'Scripts' / 'TradeBot'}")


def terminal_exe(mql5: Path) -> Path:
    """`terminal64.exe` podľa `origin.txt` dátového adresára (UTF-16 s BOM), inak z Program Files."""
    origin = mql5.parent / "origin.txt"
    if origin.exists():
        exe = Path(origin.read_text(encoding="utf-16").strip()) / "terminal64.exe"
        if exe.exists():
            return exe
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if root:
            for found in Path(root).glob("*/terminal64.exe"):
                return found
    raise SystemExit("terminal64.exe sa nenašiel; zadaj TRADEBOT_MT5_TERMINAL")


def run_config(mql5: Path, ini: Path, wait_seconds: int = 900) -> int:
    """Spustí terminál so štartovacím ini (`/config:`) a počká, kým sa sám vypne (skript `TerminalClose`,
    `[Tester] ShutdownTerminal=1`). Bežiaci terminál by ini ignoroval — preto ho najprv slušne zavrie."""
    exe = Path(os.environ.get("TRADEBOT_MT5_TERMINAL") or terminal_exe(mql5))
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/IM", exe.name], capture_output=True)
        for _ in range(60):
            alive = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe.name}"], capture_output=True, text=True).stdout
            if exe.name.lower() not in alive.lower():
                break
            time.sleep(1)
    proc = subprocess.Popen([str(exe), f"/config:{ini.resolve()}"])
    try:
        code = proc.wait(timeout=wait_seconds)
    except subprocess.TimeoutExpired:
        print(f"terminál po {wait_seconds} s stále beží (PID {proc.pid}) — beh je asi dlhší, pozri Tester log")
        return -1
    logs = sorted((mql5.parent / "logs").glob("*.log"), key=lambda p: p.stat().st_mtime)
    if logs:
        tail = logs[-1].read_text(encoding="utf-16", errors="replace").splitlines()[-8:]
        print("\n".join(line.strip() for line in tail))
    return code


def export_csv(mql5: Path, instrument: str, date_from: str | None, date_to: str | None, name: str | None) -> Path:
    """1m sviečky zo skladu ako `cas;o;h;l;c;v` (UTC, `yyyy.mm.dd hh:mm`) pre skript `TradeBotImport`."""
    from tester.ninjatrader import _frame

    inst, df = _frame(instrument, date_from, date_to)
    out = mql5 / "Files" / "TradeBot" / "import" / f"{name or inst.symbol.split('/')[0]}_1m.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        for t, o, h, l, c, v in zip(df["date"].dt.strftime("%Y.%m.%d %H:%M"), df["open"], df["high"], df["low"],
                                    df["close"], df["volume"]):
            fh.write(f"{t};{o};{h};{l};{c};{int(v)}\n")
    print(f"OK: {len(df)} barov {inst.symbol} -> {out}\n"
          f"Teraz `run deploy/mt5/ini/import_mnq.ini` (tick {inst.tick_size}, bod {inst.point_value} — sedí s TradeBotImport.set?)")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("install", "check", "profiles", "where", "csv", "run"))
    ap.add_argument("ini", nargs="?", help="run: štartovací ini terminálu (deploy/mt5/ini/*.ini)")
    ap.add_argument("--instrument", default="mnq_databento", help="csv: kľúč inštrumentu v sklade sviečok")
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--name", help="csv: názov súboru bez `_1m.csv` (default zo symbolu)")
    ap.add_argument("--wait", type=int, default=900, help="run: koľko sekúnd čakať na vypnutie terminálu")
    ap.add_argument("--mt5-dir", help="adresár MQL5 terminálu (…\\MetaQuotes\\Terminal\\<hash>\\MQL5)")
    ap.add_argument("--profile", action="append", default=[], help="ďalší profil (cesta k JSON) na export")
    args = ap.parse_args(argv)
    if args.command == "where":
        found = candidate_dirs()
        print("\n".join(str(p) for p in found) if found else "žiadny terminál MT5 v %APPDATA%\\MetaQuotes\\Terminal")
        return 0
    if sys.platform != "win32":
        raise SystemExit("MetaTrader 5 s .NET importom beží len na Windows")
    mql5 = mt5_dir(args.mt5_dir)
    try:
        if args.command == "install":
            install(mql5, args.profile)
        elif args.command == "check":
            check(mql5)
        elif args.command == "csv":
            export_csv(mql5, args.instrument, args.date_from, args.date_to, args.name)
        elif args.command == "run":
            if not args.ini:
                raise SystemExit("run: zadaj ini (deploy/mt5/ini/*.ini)")
            return run_config(mql5, Path(args.ini), args.wait)
        else:
            print(f"OK: {export_profiles(mql5, args.profile)} profilov -> {common_files(mql5) / 'TradeBot' / 'profiles'}")
    except BuildError as exc:
        raise SystemExit(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
