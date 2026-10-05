"""Import exportu z Interactive Brokers (americké akcie, TRADES 1m, len RTH) → 1m feather po rokoch.

    python -m tester.ibkr_import C:/mag7/merged
    python -m tester.ibkr_import C:/mag7/merged/AAPL_m1_2019_20261003.parquet
    python -m tester.ibkr_import C:/mag7/min1 C:/mag7/min1_patch --symbol NVDA --no-merge

### Čo prichádza
Historické bary z TWS API (`reqHistoricalData`, `whatToShow=TRADES`, `useRTH=1`,
`1 min`), jeden symbol na súbor, meno začína symbolom (`AAPL_…`). Dva tvary:

* **zlúčený** (`AAPL_m1_2019_20261003.parquet` alebo `.csv.gz`): `dt` s časovou zónou
  New York, `open, high, low, close, volume`;
* **surové bloky** (`AAPL_201901_201903.parquet`): `dt` je **naivný** čas New York,
  ceny `o, h, l, c`, navyše `average, barCount, block_*`. Bloky sa prekrývajú, preto
  sa duplicitné časy zlučujú (rozdielny obsah je v štatistike ako konflikt).

Čas baru je **začiatok** minúty. Ceny sú split-adjusted (IBKR prepočíta históriu po
splite a zaokrúhli na centy — pred splitom je cena hrubšia, než sa obchodovala),
dividendy nie. Objem je v akciách, tiež prepočítaný splitom.

### Čo import robí
1. **Čas z New Yorku do UTC** (naivný čas sa lokalizuje cez `America/New_York`,
   nejednoznačný čas je chyba, nie odhad). Ďalej je čas baru UTC ako všade v jadre.
2. **Vyhodí vypchávku.** Minútu bez obchodu IBKR vyplní plochým barom s objemom 0
   a cenou predošlého close; rada má mať bary len tam, kde sa obchodovalo (ako Databento).
3. Poistka ako pri Databento: bar s nezmyselným OHLC do rady nejde, jeden čas je jeden bar.
4. **Len hlási**, čo by mohlo byť zle, a nič s tým nerobí: bary mimo RTH a cez víkend,
   ceny mimo mriežky ticku, najväčší skok medzi dňami (neupravený split by bol desiatky %).

Ďalej je to tá istá cesta ako pri Dukascopy a Databento: feather po rokoch do
`data_archive/tester/ibkr/futures/` (trh `futures` = dá sa shortovať, nie futures
kontrakt), `tester.data_archive merge` zloží pracovný súbor, vyššie TF si Tester
dopočíta. Symbol musí byť v `tradebot/core/instruments_ibkr.json`.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from tradebot.core.paths import ARCHIVE_ROOTS, TESTER_ARCHIVE
from tradebot.core.types import INSTRUMENTS, InstrumentSpec

from .dukas_import import store

__all__ = ["ImportStats", "load_ibkr_frame", "find_sources", "resolve_symbol"]

NEW_YORK = "America/New_York"
#: Symbol na začiatku mena súboru: `AAPL_m1_…`, `BRK.B_2019…`.
SYMBOL_RE = re.compile(r"^([A-Z][A-Z0-9.]*)_")
SUFFIXES = (".parquet", ".csv.gz", ".csv")
#: Denný skok (close → open ďalšieho dňa), od ktorého sa pýta, či nejde o neupravený split.
SPLIT_SUSPECT = 0.35


@dataclass
class ImportStats:
    files: int = 0
    rows_in: int = 0
    rows_out: int = 0
    dropped_dup: int = 0        #: ten istý čas druhýkrát (prekryv blokov)
    dup_conflicts: int = 0      #: … a s iným obsahom (ostáva posledný)
    dropped_padding: int = 0    #: plochý bar s objemom 0 — minúta bez obchodu
    dropped_bad: int = 0        #: nezmyselné OHLC alebo cena <= 0
    dropped_range: int = 0
    outside_rth: int = 0        #: len hlásené
    off_tick: int = 0           #: ceny mimo mriežky ticku, len hlásené
    days: int = 0
    first: str | None = None
    last: str | None = None
    max_gap: tuple[str, float] | None = None   #: (deň, |open/predošlý close - 1|)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"suborov: {self.files}, riadkov: {self.rows_in} -> {self.rows_out}, obchodnych dni: {self.days}",
            f"duplicitne casy: {self.dropped_dup} (z toho s inym obsahom: {self.dup_conflicts})",
            f"vyhodena vypchavka (objem 0): {self.dropped_padding}, zle OHLC: {self.dropped_bad}, "
            f"mimo --from/--to: {self.dropped_range}",
            f"mimo RTH alebo cez vikend: {self.outside_rth}, ceny mimo mriezky ticku: {self.off_tick}",
            f"obdobie: {self.first} .. {self.last}",
        ]
        if self.max_gap:
            d, g = self.max_gap
            lines.append(f"najvacsi skok medzi dnami: {g * 100:.1f} % ({d})")
        lines += self.notes
        return "\n".join(lines)


def resolve_symbol(symbol: str) -> tuple[str, InstrumentSpec] | None:
    """`AAPL`, `AAPL/USD` alebo kľúč `aapl_ibkr` → (kľúč, inštrument) zo zdroja ibkr."""
    want = symbol.strip()
    for key, inst in INSTRUMENTS.items():
        if inst.data_source != "ibkr":
            continue
        if want in (key, inst.symbol) or want.upper() == inst.symbol.split("/")[0]:
            return key, inst
    return None


def symbol_of(path: Path) -> str | None:
    m = SYMBOL_RE.match(path.name)
    return m.group(1) if m else None


def find_sources(paths: list[Path]) -> dict[str, list[Path]]:
    """Súbory a adresáre (bez rekurzie) → {symbol: [súbory]} podľa mena súboru.

    Ten istý súbor v dvoch formátoch (`X.parquet` a `X.csv.gz`) sa číta raz, z parquetu.
    """
    out: dict[str, list[Path]] = {}
    for p in paths:
        files = sorted(p.iterdir()) if p.is_dir() else [p]
        stems = {f.name[: -len(".parquet")] for f in files if f.name.endswith(".parquet")}
        for f in files:
            if not f.is_file() or not f.name.endswith(SUFFIXES):
                continue
            if not f.name.endswith(".parquet") and re.sub(r"\.csv(\.gz)?$", "", f.name) in stems:
                continue
            sym = symbol_of(f)
            if sym:
                out.setdefault(sym, []).append(f)
    return out


def _read(path: Path):
    import pandas as pd

    if path.name.endswith(".parquet"):
        df = pd.read_parquet(path)
    else:
        # round_trip: to isté číslo ako v parquete, inak by prekryv vyzeral ako konflikt
        df = pd.read_csv(path, float_precision="round_trip")
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close"})
    missing = [c for c in ("dt", "open", "high", "low", "close", "volume") if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: chybaju stlpce {missing} (ma {list(df.columns)})")
    dt = df["dt"]
    if pd.api.types.is_datetime64_any_dtype(dt) and dt.dt.tz is not None:
        date = dt.dt.tz_convert("UTC")
    elif dt.astype(str).str.contains(r"[+-]\d\d:\d\d$|Z$", regex=True).all():
        # CSV: ISO s posunom, v zime -05:00 a v lete -04:00 — utc=True ich zjednotí.
        date = pd.to_datetime(dt, utc=True)
    else:
        # Surové bloky: naivný čas New York. Zmena času je vo víkendovej noci, mimo RTH,
        # takže nejednoznačný čas by znamenal zlé dáta — nech to spadne.
        date = (pd.to_datetime(dt).dt.tz_localize(NEW_YORK, ambiguous="raise", nonexistent="raise")
                .dt.tz_convert("UTC"))
    out = pd.DataFrame({"date": date.astype("datetime64[ns, UTC]")})   # ako zvyšok archívu
    for c in ("open", "high", "low", "close", "volume"):
        out[c] = df[c].astype("float64").to_numpy()
    return out


def load_ibkr_frame(paths: list[Path], *, tick_size: float = 0.01, date_from: str | None = None,
                    date_to: str | None = None, stats: ImportStats | None = None):
    """IBKR súbory jedného symbolu → rada `date, open, high, low, close, volume` (UTC)."""
    import numpy as np
    import pandas as pd

    st = stats if stats is not None else ImportStats()
    parts = [_read(Path(p)) for p in paths]
    st.files = len(parts)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["date", "open", "high", "low", "close", "volume"])
    st.rows_in = len(df)

    before = len(df)
    if date_from:
        df = df[df["date"] >= pd.Timestamp(f"{date_from} 00:00:00", tz="UTC")]
    if date_to:
        df = df[df["date"] <= pd.Timestamp(f"{date_to} 23:59:59", tz="UTC")]
    st.dropped_range = before - len(df)

    # Stabilné zoradenie: z dvoch barov s rovnakým časom ostane ten zo súboru, čo prišiel neskôr.
    df = df.sort_values("date", kind="stable")
    dup = df.duplicated("date", keep="last")
    st.dropped_dup = int(dup.sum())
    st.dup_conflicts = st.dropped_dup - int(df.duplicated(keep="last").sum())
    df = df[~dup]

    px = df[["open", "high", "low", "close"]]
    padding = (df["volume"] <= 0) & (px.max(axis=1) == px.min(axis=1))
    st.dropped_padding = int(padding.sum())
    df = df[~padding]
    zly = ((df["high"] < df["low"]) | (df["high"] < df[["open", "close"]].max(axis=1))
           | (df["low"] > df[["open", "close"]].min(axis=1))
           | (df[["open", "high", "low", "close"]] <= 0).any(axis=1) | (df["volume"] < 0))
    st.dropped_bad = int(zly.sum())
    df = df[~zly].reset_index(drop=True)
    st.rows_out = len(df)
    if df.empty:
        return df

    ny = df["date"].dt.tz_convert(NEW_YORK)
    minute = ny.dt.hour * 60 + ny.dt.minute
    st.outside_rth = int(((minute < 9 * 60 + 30) | (minute >= 16 * 60) | (ny.dt.dayofweek >= 5)).sum())
    ticks = df[["open", "high", "low", "close"]].to_numpy() / tick_size
    st.off_tick = int((np.abs(ticks - np.round(ticks)) > 1e-6).any(axis=1).sum())

    day = ny.dt.date
    st.days = int(day.nunique())
    close = df.groupby(day)["close"].last()
    opn = df.groupby(day)["open"].first()
    gap = (opn / close.shift() - 1).abs().dropna()
    if len(gap):
        st.max_gap = (str(gap.idxmax()), float(gap.max()))
        if gap.max() > SPLIT_SUSPECT:
            st.notes.append(f"POZOR: skok {gap.max() * 100:.0f} % medzi dnami ({gap.idxmax()}) "
                            f"- neupraveny split? Over to pred pouzitim.")
    st.first = f"{df['date'].iloc[0]:%Y-%m-%d %H:%M}"
    st.last = f"{df['date'].iloc[-1]:%Y-%m-%d %H:%M}"
    return df


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m tester.ibkr_import",
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("src", type=Path, nargs="+",
                    help="IBKR súbory (.parquet, .csv.gz) alebo adresáre s nimi; symbol je začiatok mena súboru")
    ap.add_argument("--symbol", action="append",
                    help="len tento symbol (AAPL alebo aapl_ibkr); dá sa opakovať")
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD, vrátane (UTC)")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD, vrátane (UTC)")
    ap.add_argument("--archive", type=Path, default=TESTER_ARCHIVE,
                    help="kam ročné feather súbory (default data_archive/tester/)")
    ap.add_argument("--no-merge", action="store_true", help="nezložiť pracovný súbor pre Tester")
    return ap


def main(argv: list[str] | None = None, stderr: TextIO | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    args = _build_parser().parse_args(argv)
    err = stderr or sys.stderr

    for p in args.src:
        if not p.exists():
            print(f"zdroj neexistuje: {p}", file=err)
            return 1
    sources = find_sources(args.src)
    if args.symbol:
        want = {}
        for s in args.symbol:
            found = resolve_symbol(s)
            name = found[1].symbol.split("/")[0] if found else s.upper()
            want[name] = sources.get(name, [])
            if not want[name]:
                print(f"pre symbol {s!r} som v zdroji nenasiel ziadny subor", file=err)
                return 1
        sources = want
    if not sources:
        print("v zdroji nie je ziadny subor <SYMBOL>_….parquet / .csv.gz", file=err)
        return 1

    resolved: dict[str, tuple[str, InstrumentSpec]] = {}
    for sym in sorted(sources):
        found = resolve_symbol(sym)
        if found is None:
            zname = ", ".join(sorted(i.symbol.split("/")[0] for i in INSTRUMENTS.values()
                                     if i.data_source == "ibkr"))
            print(f"symbol {sym!r} nie je v tradebot/core/instruments_ibkr.json; zname: {zname or '(nic)'}. "
                  f"Dopis ho tam (tick, hodnota bodu, naklad) a spusti znova.", file=err)
            return 1
        resolved[sym] = found

    rc = 0
    for sym, (key, inst) in resolved.items():
        stats = ImportStats()
        df = load_ibkr_frame(sources[sym], tick_size=inst.tick_size, date_from=args.date_from,
                             date_to=args.date_to, stats=stats)
        print(f"\n{sym}: {len(sources[sym])} suborov -> {inst.data_stem} ({key})", file=err)
        print(stats.summary(), file=err)
        if df.empty:
            print("po filtrovani neostal ziadny bar", file=err)
            rc = 1
            continue
        print("archiv (commitni ho):", file=err)
        store(df, inst, archive=args.archive, merge=False)

    if not args.no_merge:
        from . import data_archive

        data_archive.merge(verbose=False, roots=ARCHIVE_ROOTS)
        print("\npracovne subory pre Tester su zlozene; vyssie TF dopocita `python -m tester.timeframes` "
              "alebo start webapp", file=err)
    return rc


if __name__ == "__main__":
    sys.exit(main())
