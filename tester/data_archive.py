"""Rozdelí stiahnuté sviečky na ročné súbory a zase ich zloží späť.

    python -m tester.data_archive split     # po stiahnutí dát
    python -m tester.data_archive merge     # po klonovaní repozitára
    python -m tester.data_archive status

### Načo to je
Freqtrade drží celý pár+TF v **jednom** súbore, ktorý sa pri každom sťahovaní
prepíše. Git si pritom pamätá každú verziu — 86 MB `1m` súbor by tak pri každom
doťahovaní dát pridal do histórie ďalších 86 MB, ktoré sa už nedajú odstrániť
bez prepísania histórie.

Ročné súbory tento problém odstraňujú: rok 2019 sa po prvom commite už nikdy
nezmení, takže jeho blob v histórii existuje raz. Denne rastie iba súbor za
aktuálny rok.

### Ako sa to používa
Archív (`data_archive/tester/`) je to, čo je v gite. Pracovné súbory (`data/`) sú z neho
odvodené a v `.gitignore`.

    stiahnutie dat  ->  data/  ->  split  ->  data_archive/tester/  ->  commit
    klon            ->  data_archive/tester/  ->  merge  ->  data/  ->  backtest

Platformy majú vlastné korene (`tradebot.core.paths.ARCHIVE_ROOTS`) — burzové sviečky
pod `deploy/freqtrade/user_data/`, Dukascopy 1m sviečky pod
`deploy/multicharts/`. Formát súborov je rovnaký, príkaz prejde oba.

Delenie je **bezstratové** — `merge(split(x))` dá presne to isté, čo bolo v `x`.
Overuje to `tester/tests/test_data_archive.py`.

Žiadne sviečky sa tu nedopočítavajú ani neupravujú, len sa presúvajú medzi
súbormi — na disku sú výhradne skutočné dáta, tak ako prišli z burzy či z exportu.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from tradebot.core.paths import ARCHIVE_ROOTS

#: Dvojice (archív, pracovný adresár). Testy si ich prepisujú.
ROOTS: tuple[tuple[Path, Path], ...] = ARCHIVE_ROOTS

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


def split_root(archive: Path, data: Path, verbose: bool = True) -> list[Path]:
    """`data/` -> `data_archive/tester/` jedného koreňa, jeden súbor na rok."""
    written: list[Path] = []
    for src in sorted(data.rglob("*.feather")):
        rel = src.relative_to(data)
        df = _read(src)
        if "date" not in df.columns or df.empty:
            if verbose:
                print(f"  preskakujem {rel} (nema stlpec date alebo je prazdny)")
            continue

        years = df["date"].dt.year
        for year in sorted(years.unique()):
            part = df[years == year]
            out = archive / rel.parent / f"{_stem(src)}.{year}.feather"
            # Zapisujeme len ak sa obsah naozaj zmenil - inak by git videl novy
            # blob aj pri roku, ktory sa nemenil (feather nie je bajtovo stabilny).
            if out.exists() and len(_read(out)) == len(part):
                continue
            _write(part, out)
            written.append(out)
            if verbose:
                print(f"  {out.relative_to(archive)}  {len(part):>8} barov")
    return written


def merge_root(archive: Path, data: Path, verbose: bool = True) -> list[Path]:
    """`data_archive/tester/` -> `data/` jedného koreňa."""
    import pandas as pd

    groups: dict[Path, list[Path]] = {}
    for src in sorted(archive.rglob("*.feather")):
        m = _YEAR_SUFFIX.search(src.name)
        if not m:
            continue
        base = src.name[: m.start()] + ".feather"
        groups.setdefault(src.parent.relative_to(archive) / base, []).append(src)

    out_paths: list[Path] = []
    for rel, parts in sorted(groups.items()):
        df = pd.concat([_read(p) for p in sorted(parts)], ignore_index=True)
        df = df.sort_values("date").drop_duplicates(subset="date", keep="last")
        out = data / rel
        _write(df, out)
        out_paths.append(out)
        if verbose:
            print(f"  {rel}  {len(df):>8} barov z {len(parts)} rokov")
    return out_paths


def split(verbose: bool = True, roots: tuple[tuple[Path, Path], ...] | None = None) -> list[Path]:
    """`data/` -> `data_archive/tester/` vo všetkých koreňoch. Vráti zapísané súbory."""
    written: list[Path] = []
    for archive, data in roots if roots is not None else ROOTS:
        if data.exists():
            written += split_root(archive, data, verbose=verbose)
    return written


def merge(verbose: bool = True, roots: tuple[tuple[Path, Path], ...] | None = None) -> list[Path]:
    """`data_archive/tester/` -> `data/` vo všetkých koreňoch. Vráti zložené súbory."""
    out: list[Path] = []
    for archive, data in roots if roots is not None else ROOTS:
        if archive.exists():
            out += merge_root(archive, data, verbose=verbose)
    return out


def status() -> int:
    for archive, data in ROOTS:
        print(f"pracovne subory ({data}):")
        work = sorted(data.rglob("*.feather")) if data.exists() else []
        if not work:
            print("  ziadne - spusti `merge`")
        for p in work:
            df = _read(p)
            span = f"{df['date'].min():%Y-%m-%d} -> {df['date'].max():%Y-%m-%d}" if len(df) else "-"
            print(f"  {p.relative_to(data)}  {len(df):>8} barov  {span}  {p.stat().st_size/1e6:.1f} MB")

        print(f"\narchiv ({archive}):")
        arch = sorted(archive.rglob("*.feather")) if archive.exists() else []
        if not arch:
            print("  ziadny - spusti `split`")
        total = 0
        for p in arch:
            total += p.stat().st_size
            print(f"  {p.relative_to(archive)}  {p.stat().st_size/1e6:>6.1f} MB")
        if arch:
            print(f"  {'spolu':<52} {total/1e6:>6.1f} MB")
        print()
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

    print("Skladam rocne subory z archivu...")
    if not any(archive.exists() for archive, _ in ROOTS):
        print(f"Ziadny archiv neexistuje: {', '.join(str(a) for a, _ in ROOTS)}", file=sys.stderr)
        return 1
    n = merge(verbose=not args.quiet)
    print(f"\nZlozenych {len(n)} suborov.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
