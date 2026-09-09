"""Import surového Dukascopy exportu: vyčistí ho, spraví 1m feather a rozdelí po rokoch.

    python -m tester.dukas_import C:/dukas/NAS100_M1_10Y.csv --symbol NAS100
    python -m tester.dukas_import C:/dukas/EURUSD_M1.csv --symbol EURUSD \\
        --point-value 100000 --tick 0.00001
    python -m tester.dukas_import C:/dukas/US500_M1.csv --symbol US500 \\
        --point-value 1 --fix-scale --from 2021-01-01

### Kam to patrí v ceste dát
Importér je **jeden na zdroj** a robí vždy to isté: vyčistí surový súbor, prevedie ho do
feather v tom timeframe, v akom sú surové dáta (Dukascopy = 1m), rozdelí po rokoch a uloží
do `data_archive/`. Tam jeho práca končí — v archíve je len to, čo naozaj prišlo zo zdroja.

    raw  ->  import (čistenie, feather v TF zdroja, split po rokoch)  ->  data_archive/
    data_archive/  ->  merge  ->  data/tester/  ->  vyššie TF, export pre QuoteManager

Zvyšok si spraví Tester sám: `tester.data_archive merge` zloží pracovné súbory,
`tester.timeframes` (alebo Freqtrade adaptér počas behu) dopočíta vyššie timeframy a
`tester.quotemanager` vyrobí ASCII súbor pre QuoteManager. Nič z toho tu už nie je.

### Čo sa pri čistení robí
1. **Vypchávka.** Dukascopy export má riadok pre každú minútu vrátane víkendov a
   prestávok — plochý bar `o=h=l=c` s cenou posledného uzavretia, opakovaný dookola
   (~40 % súboru). Berie sa ako skutočný bar a stratégia by ho počítala do limitov
   `*MaxBars` (sú v baroch), do ATR aj do SMA objemu. Vyhadzujú sa riadky, ktoré
   nenesú žiadnu informáciu: plochý bar s cenou rovnou predchádzajúcemu uzavretiu.
   Skutočná plochá minúta (cena sa oproti minulému baru pohla a stála) ostáva.
2. **Mierka.** Niektoré exporty (US500 2015–2019) majú celé dni s cenou ×1000.
   Nástroj to nahlási vždy; opraví len s `--fix-scale` (delí/násobí 1000 podľa mediánu
   ceny v súbore). Predtým sa mierka opravovala len v ASCII výstupe pre QuoteManager,
   takže archív si glitch niesol ďalej — teraz sa čistí to, čo sa ukladá.
3. **Čas baru** ostáva časom **otvorenia**, ako v jadre a v Pine. Posun na čas zatvorenia
   (konvencia MultiCharts) rieši až export pre QuoteManager.
4. **Objem** ostáva taký, aký je — tickový (loty klientov, nie burzový obrat). Inštrument
   má `has_real_volume=False` a `useVolumeFilter` treba nechať vypnutý.

**Nový symbol** stačí pomenovať: `--symbol EURUSD --point-value 100000 --tick 0.00001`
dopíše riadok do `tradebot/core/instruments_dukascopy.json` (odtiaľ ho vidí webapp,
emulátor aj MultiCharts študia) a vyrobí kostru profilu v `docs/profily_archiv/ibs/`.
Hodnota bodu musí sedieť s **Big Point Value** symbolu v QuoteManageri, inak by sizing
v MultiCharts a v Testeri nebol ten istý.

Čas v Dukascopy exporte je UTC; v QuoteManageri sa pri importe volí ako časové pásmo
súboru GMT.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from tradebot.core.paths import ARCHIVE_ROOTS, REPO, TESTER_ARCHIVE
from tradebot.core.types import DUKASCOPY_REGISTRY, INSTRUMENTS, InstrumentSpec, dukascopy_specs

__all__ = [
    "ImportStats", "load_dukas_frame", "scale_reference", "write_years", "store",
    "resolve_symbol", "register_symbol", "write_profile_skeleton",
]

#: Odchýlka ceny od mediánu, od ktorej je riadok "inou mierkou" (×1000 glitch).
#: Za desať rokov sa index pohne ~5×, takže 100× je bezpečne mimo.
SCALE_RATIO = 100.0
SCALE_FACTOR = 1000.0

#: Kostra profilu pre nový symbol sa berie odtiaľto — je to najbližší hotový
#: Dukascopy profil (prahy v bodoch odvodené z MNQ).
PROFILE_TEMPLATE = REPO / "docs" / "profily_archiv" / "ibs" / "nas100_dukas_3m.json"
PROFILE_DIR = REPO / "docs" / "profily_archiv" / "ibs"


# --------------------------------------------------------------------------- #
# Čistenie a prevod do feather
# --------------------------------------------------------------------------- #


@dataclass
class ImportStats:
    rows_in: int = 0
    rows_out: int = 0
    dropped_padding: int = 0
    dropped_range: int = 0
    scale_outliers: int = 0
    scale_fixed: int = 0
    first: str | None = None
    last: str | None = None
    reference: float | None = None
    #: dni (YYYY-MM-DD), na ktorých boli riadky inej mierky — na kontrolu
    outlier_days: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"riadkov: {self.rows_in} -> {self.rows_out}",
            f"vyhodena vypchavka: {self.dropped_padding}",
            f"mimo --from/--to: {self.dropped_range}",
            f"obdobie: {self.first} .. {self.last}",
        ]
        if self.reference is not None:
            lines.append(f"referencna cena (median): {self.reference:g}")
        if self.scale_outliers:
            what = "opravene" if self.scale_fixed else "NEOPRAVENE (daj --fix-scale)"
            days = ", ".join(self.outlier_days[:8]) + (" ..." if len(self.outlier_days) > 8 else "")
            lines.append(f"riadky inej mierky: {self.scale_outliers} {what}; dni: {days}")
        return "\n".join(lines)


def scale_reference(close) -> float | None:
    """Referenčná cena súboru — horný medián uzavretí. Podľa nej sa poznajú riadky ×1000."""
    import numpy as np

    values = np.asarray(close, dtype="float64")
    values = values[~np.isnan(values)]
    if not len(values):
        return None
    return float(np.sort(values)[len(values) // 2])


def load_dukas_frame(path: str | Path, *, drop_padding: bool = True, fix_scale: bool = False,
                     date_from: str | None = None, date_to: str | None = None,
                     stats: ImportStats | None = None):
    """Dukascopy CSV (`dt,o,h,l,c,vol`, UTC, čas otvorenia) → vyčistený DataFrame sviečok.

    Jediné miesto, kde sa surové dáta čistia — všetko ostatné už číta výsledok z archívu.
    """
    import pandas as pd

    st = stats if stats is not None else ImportStats()
    df = pd.read_csv(
        path, usecols=[0, 1, 2, 3, 4, 5], header=0,
        names=["date", "open", "high", "low", "close", "volume"],
        dtype={"open": "float64", "high": "float64", "low": "float64",
               "close": "float64", "volume": "float64"},
    )
    df["date"] = pd.to_datetime(df["date"], utc=True)
    st.rows_in = len(df)

    if drop_padding:
        flat = (df["open"] == df["close"]) & (df["high"] == df["low"]) & (df["open"] == df["high"])
        padding = flat & (df["close"] == df["close"].shift(1))
        st.dropped_padding = int(padding.sum())
        df = df[~padding]

    st.reference = scale_reference(df["close"])
    if st.reference:
        ohlc = ["open", "high", "low", "close"]
        high = df["close"] > st.reference * SCALE_RATIO
        low = df["close"] < st.reference / SCALE_RATIO
        st.scale_outliers = int((high | low).sum())
        st.outlier_days = sorted({d.strftime("%Y-%m-%d") for d in df.loc[high | low, "date"]})
        if fix_scale and st.scale_outliers:
            df = df.copy()
            df.loc[high, ohlc] = df.loc[high, ohlc] / SCALE_FACTOR
            df.loc[low, ohlc] = df.loc[low, ohlc] * SCALE_FACTOR
            st.scale_fixed = st.scale_outliers

    before = len(df)
    if date_from:
        df = df[df["date"] >= f"{date_from} 00:00:00+00:00"]
    if date_to:
        df = df[df["date"] <= f"{date_to} 23:59:59+00:00"]
    st.dropped_range = before - len(df)

    df = df.reset_index(drop=True)
    st.rows_out = len(df)
    if len(df):
        st.first = f"{df['date'].iloc[0]:%Y-%m-%d %H:%M}"
        st.last = f"{df['date'].iloc[-1]:%Y-%m-%d %H:%M}"
    return df


def write_years(df, stem: str, *, archive: Path = TESTER_ARCHIVE, from_year: int | None = None,
                to_year: int | None = None, verbose: bool = True) -> list[Path]:
    """Rok = jeden súbor. Uzavretý rok sa už nezmení, takže jeho blob je v gite raz."""
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


def store(df, inst: InstrumentSpec, *, archive: Path = TESTER_ARCHIVE, merge: bool = True,
          verbose: bool = True, roots: tuple[tuple[Path, Path], ...] | None = None) -> list[Path]:
    """Vyčistené sviečky → ročné súbory v archíve (+ pracovná kópia pre Tester).

    Spoločný koniec každého importu, nech je zdroj akýkoľvek: do archívu ide timeframe
    zdroja, zvyšok si Tester dopočíta z neho.
    """
    written = write_years(df, inst.data_stem, archive=archive / inst.data_source / inst.market,
                          verbose=verbose)
    if merge:
        from . import data_archive

        data_archive.merge(verbose=False, roots=roots or ARCHIVE_ROOTS)
    return written


# --------------------------------------------------------------------------- #
# Symboly: tabuľka Dukascopy inštrumentov
# --------------------------------------------------------------------------- #


def resolve_symbol(symbol: str) -> tuple[str, InstrumentSpec] | None:
    """Nájde inštrument podľa kľúča (`nas100_dukascopy`), symbolu (`NAS100/USD`) alebo mena (`NAS100`)."""
    want = symbol.strip()
    for key, inst in INSTRUMENTS.items():
        if inst.venue != "multicharts":
            continue
        if want in (key, inst.symbol, inst.exchange_symbol) or want.upper() == inst.exchange_symbol:
            return key, inst
    return None


def register_symbol(
    symbol: str,
    *,
    point_value: float,
    tick_size: float = 0.01,
    qty_step: float = 1.0,
    min_qty: float = 1.0,
    currency: str = "USD",
    note: str = "",
    registry: Path | None = None,
) -> tuple[str, InstrumentSpec]:
    """Dopíše symbol do `instruments_dukascopy.json` a sprístupní ho v `INSTRUMENTS`.

    Kľúč je `<symbol>_dukascopy`, pár `<SYMBOL>/<mena>` — rovnaká konvencia ako NAS100.
    """
    path = registry or DUKASCOPY_REGISTRY
    name = symbol.strip().upper().split("/")[0]
    key = f"{name.lower()}_dukascopy"
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    raw[key] = {
        "symbol": f"{name}/{currency.upper()}",
        "tick_size": tick_size,
        "point_value": point_value,
        "qty_step": qty_step,
        "min_qty": min_qty,
        "quote_currency": currency.upper(),
        "note": note or f"Dukascopy CFD {name}; hodnota bodu musi sediet s Big Point Value v QuoteManageri.",
    }
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    INSTRUMENTS.update(dukascopy_specs(path))
    return key, INSTRUMENTS[key]


def write_profile_skeleton(key: str, inst: InstrumentSpec, *, template: Path = PROFILE_TEMPLATE,
                           out_dir: Path = PROFILE_DIR) -> Path:
    """Kostra profilu pre nový symbol — kópia NAS100 profilu s vymeneným inštrumentom.

    Prahy v bodoch prevzaté z MNQ sedia len na podklade s podobnou mierkou pohybu
    (NAS100). Na inom trhu (forex, komodity) ich treba prepnúť na jednotku `atr` —
    hlási to aj výstup príkazu.
    """
    data = json.loads(template.read_text(encoding="utf-8"))
    name = inst.exchange_symbol
    data["_title"] = f"MultiCharts {name} CFD (Dukascopy) 3m — kostra z {template.stem}"
    data["_comment"] = [
        f"Kostra vyrobena prikazom `python -m tester.dukas_import ... --symbol {name}`.",
        f"Instrument {key}: tick {inst.tick_size:g}, hodnota bodu {inst.point_value:g} {inst.quote_currency}.",
        "PREVERIT: prahy v bodoch (unit abs) su prevzate z MNQ a sedia len na podobnom podklade;",
        "na inom trhu ich prepni na jednotku atr (`--set minImbSizePoints=0.5@atr`).",
        "Objem Dukascopy je len tickovy - useVolumeFilter nechaj vypnuty.",
    ]
    data["_instrument"] = key
    data["tickDollarValue"] = inst.tick_dollar_value
    out = out_dir / f"{name.lower()}_dukas_3m.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m tester.dukas_import",
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("src", type=Path, help="Dukascopy CSV: dt,o,h,l,c,vol (1m, UTC)")
    ap.add_argument("--symbol", required=True,
                    help="meno symbolu (NAS100, EURUSD…) alebo kľúč inštrumentu (nas100_dukascopy)")
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD, vrátane")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD, vrátane")
    ap.add_argument("--fix-scale", action="store_true", help="opraviť riadky s cenou ×1000 / ÷1000")
    ap.add_argument("--keep-padding", action="store_true", help="nevyhadzovať ploché opakované bary")
    ap.add_argument("--archive", type=Path, default=TESTER_ARCHIVE,
                    help="kam ročné feather súbory (default data_archive/tester/)")
    ap.add_argument("--no-merge", action="store_true", help="nezložiť pracovný súbor pre Tester")

    new = ap.add_argument_group("nový symbol (ak ešte nie je v tabuľke)")
    new.add_argument("--point-value", type=float, help="$ za pohyb ceny o 1.0 na jednotku = Big Point Value")
    new.add_argument("--tick", type=float, default=0.01, help="najmenší krok ceny (predvolene 0.01)")
    new.add_argument("--currency", default="USD", help="mena kótovania (predvolene USD)")
    new.add_argument("--qty-step", type=float, default=1.0)
    new.add_argument("--min-qty", type=float, default=1.0)
    new.add_argument("--no-profile", action="store_true", help="nevyrábať kostru profilu")
    return ap


def _instrument(args, err: TextIO) -> tuple[str, InstrumentSpec] | None:
    found = resolve_symbol(args.symbol)
    if found is not None:
        if args.point_value is not None and args.point_value != found[1].point_value:
            print(f"POZOR: {found[0]} uz existuje s hodnotou bodu {found[1].point_value:g}, "
                  f"--point-value {args.point_value:g} sa ignoruje (uprav tabulku rucne).", file=err)
        return found
    if args.point_value is None:
        known = ", ".join(sorted(k for k, i in INSTRUMENTS.items() if i.venue == "multicharts"))
        print(f"symbol {args.symbol!r} v tabulke nie je. Pridas ho tym, ze das --point-value "
              f"(Big Point Value z QuoteManagera), pripadne --tick a --currency.\n"
              f"zname Dukascopy symboly: {known}", file=err)
        return None
    key, inst = register_symbol(
        args.symbol, point_value=args.point_value, tick_size=args.tick,
        qty_step=args.qty_step, min_qty=args.min_qty, currency=args.currency,
    )
    print(f"novy symbol {inst.symbol} -> {DUKASCOPY_REGISTRY.name} ({key}); commitni ten subor", file=err)
    if not args.no_profile:
        prof = write_profile_skeleton(key, inst)
        print(f"kostra profilu: {prof.relative_to(REPO)} — PREVER prahy (viď _comment v subore)", file=err)
    return key, inst


def main(argv: list[str] | None = None, stderr: TextIO | None = None) -> int:
    # Windows konzola beží v cp1250 a na ‚→‘ v nápovede by spadla na UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pytest capsys, presmerovanie
            pass
    args = _build_parser().parse_args(argv)
    err = stderr or sys.stderr  # až tu, aby pytest capsys videl výstup

    if not args.src.exists():
        print(f"zdroj neexistuje: {args.src}", file=err)
        return 1
    resolved = _instrument(args, err)
    if resolved is None:
        return 1
    _, inst = resolved

    stats = ImportStats()
    df = load_dukas_frame(
        args.src, drop_padding=not args.keep_padding, fix_scale=args.fix_scale,
        date_from=args.date_from, date_to=args.date_to, stats=stats,
    )
    print(f"\n{args.src.name} -> {inst.data_stem}", file=err)
    print(stats.summary(), file=err)
    if df.empty:
        print("po cisteni a orezani neostal ziadny bar", file=err)
        return 1

    print("\narchiv (commitni ho):", file=err)
    files = store(df, inst, archive=args.archive, merge=not args.no_merge)
    print(f"zapisanych {len(files)} rocnych suborov do {args.archive}", file=err)
    if not args.no_merge:
        from . import engines

        print(f"pracovny subor: {engines.one_minute_file(inst)}", file=err)
    print(f"par {inst.exchange_symbol} je po restarte webapp v ponuke Novy beh; "
          f"vyssie TF si Tester dopocita sam", file=err)
    print(f"CSV pre QuoteManager: python -m tester.quotemanager --symbol {inst.exchange_symbol}",
          file=err)

    if stats.scale_outliers and not args.fix_scale:
        print("POZOR: subor obsahuje riadky inej mierky a neboli opravene (--fix-scale).", file=err)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
