"""Dukascopy 1m CSV → ročné feather súbory pre webapp „burzu" MultiCharts.

    python -m tradebot.tools.dukas_archive C:/dukas/NAS100_M1_10Y.csv --instrument nas100_dukascopy --from-year 2021
    python -m tradebot.tools.data_archive merge      # potom: data_archive/ -> data/ pre webapp

Výstup: `platforms/freqtrade/user_data/data_archive/multicharts/<STEM>-1m.<rok>.feather`
(`STEM` = symbol inštrumentu bez `/`, napr. `NAS100_USD`), rovnaký tvar ako Freqtrade
sviečky (`date` UTC, open, high, low, close, volume). Vypchávka Dukascopy exportu (plochý
bar s cenou predchádzajúceho uzavretia) sa zahadzuje rovnakým pravidlom ako pri prevode pre
MultiCharts (`dukas_to_mc`) a v simulátore, takže webapp, MultiCharts aj simulátor vidia
tie isté bary. Roky sa nemenia, preto sa dajú commitovať ako ostatné dáta v archíve.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core.types import INSTRUMENTS

__all__ = ["load_dukas_frame", "write_years", "ARCHIVE_DIR"]

REPO = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = REPO / "platforms" / "freqtrade" / "user_data" / "data_archive" / "multicharts"


def load_dukas_frame(path: str | Path, *, drop_padding: bool = True):
    """Dukascopy CSV (`dt,o,h,l,c,vol`, UTC, čas otvorenia) → DataFrame v tvare Freqtrade sviečok."""
    import pandas as pd

    df = pd.read_csv(
        path, usecols=[0, 1, 2, 3, 4, 5], header=0,
        names=["date", "open", "high", "low", "close", "volume"],
        dtype={"open": "float64", "high": "float64", "low": "float64", "close": "float64", "volume": "float64"},
    )
    df["date"] = pd.to_datetime(df["date"], utc=True)
    if drop_padding:
        flat = (df["open"] == df["close"]) & (df["high"] == df["low"]) & (df["open"] == df["high"])
        padding = flat & (df["close"] == df["close"].shift(1))
        df = df[~padding]
    return df.reset_index(drop=True)


def write_years(df, stem: str, *, archive: Path = ARCHIVE_DIR, from_year: int | None = None,
                to_year: int | None = None, verbose: bool = True) -> list[Path]:
    written: list[Path] = []
    years = df["date"].dt.year
    for year in sorted(years.unique()):
        if (from_year is not None and year < from_year) or (to_year is not None and year > to_year):
            continue
        part = df[years == year].reset_index(drop=True)
        out = archive / f"{stem}-1m.{year}.feather"
        out.parent.mkdir(parents=True, exist_ok=True)
        part.to_feather(out)
        written.append(out)
        if verbose:
            print(f"  {out.name}  {len(part):>8} barov  {out.stat().st_size / 1e6:.1f} MB")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src", type=Path, help="Dukascopy 1m CSV")
    ap.add_argument("--instrument", required=True, help="kľúč z INSTRUMENTS (venue multicharts), napr. nas100_dukascopy")
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument("--archive", type=Path, default=ARCHIVE_DIR)
    args = ap.parse_args(argv)

    inst = INSTRUMENTS.get(args.instrument)
    if inst is None:
        print(f"neznamy instrument {args.instrument!r}; zname: {sorted(INSTRUMENTS)}", file=sys.stderr)
        return 1
    if inst.venue != "multicharts":
        print(f"{args.instrument} nie je instrument burzy multicharts (venue={inst.venue})", file=sys.stderr)
        return 1
    df = load_dukas_frame(args.src)
    print(f"{args.src.name}: {len(df)} 1m barov {df['date'].min():%Y-%m-%d} .. {df['date'].max():%Y-%m-%d} -> {inst.data_stem}")
    files = write_years(df, inst.data_stem, archive=args.archive, from_year=args.from_year, to_year=args.to_year)
    print(f"zapisanych {len(files)} suborov do {args.archive}; potom: python -m tradebot.tools.data_archive merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
