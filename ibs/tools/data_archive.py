"""Rozdelí stiahnuté sviečky na ročné súbory a zase ich zloží späť.

    python -m ibs.tools.data_archive split     # po stiahnutí dát
    python -m ibs.tools.data_archive merge     # po klonovaní repozitára
    python -m ibs.tools.data_archive status

### Načo to je
Freqtrade drží celý pár+TF v **jednom** súbore, ktorý sa pri každom sťahovaní
prepíše. Git si pritom pamätá každú verziu — 86 MB `1m` súbor by tak pri každom
doťahovaní dát pridal do histórie ďalších 86 MB, ktoré sa už nedajú odstrániť
bez prepísania histórie.

Ročné súbory tento problém odstraňujú: rok 2019 sa po prvom commite už nikdy
nezmení, takže jeho blob v histórii existuje raz. Denne rastie iba súbor za
aktuálny rok.

### Ako sa to používa
Archív (`data_archive/`) je to, čo je v gite. Pracovné súbory pre Freqtrade
(`data/`) sú z neho odvodené a v `.gitignore`.

    stiahnutie dat  ->  data/  ->  split  ->  data_archive/  ->  commit
    klon            ->  data_archive/  ->  merge  ->  data/  ->  backtest

Delenie je **bezstratové** — `merge(split(x))` dá presne to isté, čo bolo v `x`.
Overuje to `ibs/tests/test_data_archive.py`.

Žiadne sviečky sa tu nedopočítavajú ani neupravujú, len sa presúvajú medzi
súbormi — na disku sú výhradne skutočné burzové dáta.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "platforms" / "freqtrade" / "user_data" / "data"
ARCHIVE = REPO / "platforms" / "freqtrade" / "user_data" / "data_archive"

#: `BTC_USDT_USDT-1m-futures.feather` -> ročný `BTC_USDT_USDT-1m-futures.2019.feather`
_YEAR_SUFFIX = re.compile(r"\.(\d{4})\.feather$")


def _stem(path: Path) -> str:
    return path.name[: -len(".feather")]


def _read(path: Path):
    import pandas as pd

    return pd.read_feather(path)


def _write(df, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index(drop=True).to_feather(path)


def split(verbose: bool = True) -> list[Path]:
    """`data/` -> `data_archive/`, jeden súbor na rok. Vráti zapísané súbory."""
    written: list[Path] = []
    for src in sorted(DATA.rglob("*.feather")):
        rel = src.relative_to(DATA)
        df = _read(src)
        if "date" not in df.columns or df.empty:
            if verbose:
                print(f"  preskakujem {rel} (nema stlpec date alebo je prazdny)")
            continue

        years = df["date"].dt.year
        for year in sorted(years.unique()):
            part = df[years == year]
            out = ARCHIVE / rel.parent / f"{_stem(src)}.{year}.feather"
            # Zapisujeme len ak sa obsah naozaj zmenil - inak by git videl novy
            # blob aj pri roku, ktory sa nemenil (feather nie je bajtovo stabilny).
            if out.exists() and len(_read(out)) == len(part):
                continue
            _write(part, out)
            written.append(out)
            if verbose:
                print(f"  {out.relative_to(ARCHIVE)}  {len(part):>8} barov")
    return written


def merge(verbose: bool = True) -> list[Path]:
    """`data_archive/` -> `data/`. Vráti zložené súbory."""
    import pandas as pd

    groups: dict[Path, list[Path]] = {}
    for src in sorted(ARCHIVE.rglob("*.feather")):
        m = _YEAR_SUFFIX.search(src.name)
        if not m:
            continue
        base = src.name[: m.start()] + ".feather"
        groups.setdefault(src.parent.relative_to(ARCHIVE) / base, []).append(src)

    out_paths: list[Path] = []
    for rel, parts in sorted(groups.items()):
        df = pd.concat([_read(p) for p in sorted(parts)], ignore_index=True)
        df = df.sort_values("date").drop_duplicates(subset="date", keep="last")
        out = DATA / rel
        _write(df, out)
        out_paths.append(out)
        if verbose:
            print(f"  {rel}  {len(df):>8} barov z {len(parts)} rokov")
    return out_paths


def status() -> int:
    import pandas as pd

    print(f"pracovne subory ({DATA}):")
    work = sorted(DATA.rglob("*.feather"))
    if not work:
        print("  ziadne - spusti `merge`")
    for p in work:
        df = _read(p)
        span = f"{df['date'].min():%Y-%m-%d} -> {df['date'].max():%Y-%m-%d}" if len(df) else "-"
        print(f"  {p.relative_to(DATA)}  {len(df):>8} barov  {span}  {p.stat().st_size/1e6:.1f} MB")

    print(f"\narchiv ({ARCHIVE}):")
    arch = sorted(ARCHIVE.rglob("*.feather"))
    if not arch:
        print("  ziadny - spusti `split`")
    total = 0
    for p in arch:
        total += p.stat().st_size
        print(f"  {p.relative_to(ARCHIVE)}  {p.stat().st_size/1e6:>6.1f} MB")
    if arch:
        print(f"  {'spolu':<52} {total/1e6:>6.1f} MB")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("command", choices=["split", "merge", "status"])
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.command == "status":
        return status()
    if args.command == "split":
        print("Delim na rocne subory...")
        n = split(verbose=not args.quiet)
        print(f"\nZapisanych {len(n)} suborov. Nezmenene roky sa preskocili.")
        return 0

    print("Skladam rocne subory pre Freqtrade...")
    if not ARCHIVE.exists():
        print(f"Archiv neexistuje: {ARCHIVE}", file=sys.stderr)
        return 1
    n = merge(verbose=not args.quiet)
    print(f"\nZlozenych {len(n)} suborov.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
