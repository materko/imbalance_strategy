"""Surový Dukascopy export → dáta pre Tester (webapp) aj pre MultiCharts, jedným príkazom.

    python -m tradebot.tools.dukas_import C:/dukas/NAS100_M1_10Y.csv --symbol NAS100
    python -m tradebot.tools.dukas_import C:/dukas/EURUSD_M1.csv --symbol EURUSD \\
        --point-value 100000 --tick 0.00001 --target tester
    python -m tradebot.tools.dukas_import C:/dukas/US500_M1.csv --symbol US500 \\
        --point-value 1 --fix-scale --from 2021-01-01

Vyrobí dve veci (`--target tester | multicharts | both`, predvolene obe):

**Tester** — ročné feather súbory `platforms/multicharts/data_archive/<STEM>-1m.<rok>.feather`
(commitujú sa) a hneď z nich zloží pracovný súbor v `platforms/multicharts/data/`. Pár je
potom v ponuke webapp; beží cez emulátor MultiCharts, nie cez Freqtrade (Dukascopy CFD nie
sú ccxt burza). Čas baru ostáva časom **otvorenia**, ako v jadre a v Pine.

**MultiCharts** — jeden ASCII súbor pre QuoteManager s hlavičkou
`Date,Time,Open,High,Low,Close,Volume`, čas **zatvorenia** baru a objem ako celé číslo.

Obe cesty čistia export rovnakým pravidlom, takže webapp, MultiCharts aj offline
simulátor (`scan_trades --csv`) vidia tie isté bary:

1. **Vypchávka.** Dukascopy export má riadok pre každú minútu vrátane víkendov a
   prestávok — plochý bar `o=h=l=c` s cenou posledného uzavretia, opakovaný dookola
   (~40 % súboru). Berie sa ako skutočný bar a stratégia by ho počítala do limitov
   `*MaxBars` (sú v baroch), do ATR aj do SMA objemu. Vyhadzujú sa riadky, ktoré
   nenesú žiadnu informáciu: plochý bar s cenou rovnou predchádzajúcemu uzavretiu.
   Skutočná plochá minúta (cena sa oproti minulému baru pohla a stála) ostáva.
2. **Čas baru.** Dukascopy razí bar časom OTVORENIA, MultiCharts časom ZATVORENIA.
   Do QuoteManagera sa preto k času pripočíta jedna minúta (`--stamp close`); ak import
   dostane prepínač na čas otvorenia, daj `--stamp open`. Feather pre Tester si čas
   otvorenia ponecháva vždy.
3. **Mierka.** Niektoré exporty (US500 2015–2019) majú celé dni s cenou ×1000.
   Nástroj to nahlási vždy; opraví len s `--fix-scale` (delí/násobí 1000 podľa
   mediánu ceny v súbore).
4. **Objem.** QuoteManager berie len celé číslo, Dukascopy CFD majú objem v lotoch
   s desatinami (0.01), preto sa zapisuje ako `round(vol × --volume-scale)`; predvolené
   100 znamená, že sa väčšina barov nezaokrúhli na nulu. Objem je aj tak len tickový
   (loty klientov, nie burzový obrat) — inštrument má `has_real_volume=False`
   a `useVolumeFilter` treba nechať vypnutý.

**Nový symbol** stačí pomenovať: `--symbol EURUSD --point-value 100000 --tick 0.00001`
dopíše riadok do `tradebot/core/instruments_dukascopy.json` (odtiaľ ho vidí webapp,
emulátor aj MultiCharts študia) a vyrobí kostru profilu v `docs/profily_archiv/ibs/`.
Hodnota bodu musí sedieť s **Big Point Value** symbolu v QuoteManageri, inak by sizing
v MultiCharts a v Testeri nebol ten istý.

Čas v Dukascopy exporte je UTC; v QuoteManageri sa pri importe volí ako časové pásmo
súboru GMT. Súbor sa pre MultiCharts číta prúdom, takže 375 MB desaťročný export prejde
bez toho, aby sa celý načítal do pamäte (feather cesta pandas potrebuje).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Sequence, TextIO

from ..core.paths import DUKASCOPY_FT_DATA, MULTICHARTS_ARCHIVE, MULTICHARTS_DATA, REPO
from ..core.types import DUKASCOPY_REGISTRY, INSTRUMENTS, InstrumentSpec, dukascopy_specs
from .candles import resample_ohlcv

__all__ = [
    "ConvertStats", "convert", "convert_lines", "scale_reference",
    "load_dukas_frame", "write_years", "write_freqtrade",
    "resolve_symbol", "register_symbol", "write_profile_skeleton",
]

#: Odchýlka ceny od mediánu, od ktorej je riadok "inou mierkou" (×1000 glitch).
#: Za desať rokov sa index pohne ~5×, takže 100× je bezpečne mimo.
SCALE_RATIO = 100.0
SCALE_FACTOR = 1000.0
MINUTE = timedelta(minutes=1)

#: Kostra profilu pre nový symbol sa berie odtiaľto — je to najbližší hotový
#: Dukascopy profil (prahy v bodoch odvodené z MNQ).
PROFILE_TEMPLATE = REPO / "docs" / "profily_archiv" / "ibs" / "nas100_dukas_3m.json"
PROFILE_DIR = REPO / "docs" / "profily_archiv" / "ibs"


# --------------------------------------------------------------------------- #
# Prevod riadkov (spoločný pre obe cesty)
# --------------------------------------------------------------------------- #


@dataclass
class ConvertStats:
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


def _parse(line: str) -> tuple[str, float, float, float, float, float] | None:
    parts = line.rstrip("\r\n").split(",")
    if len(parts) < 6 or not parts[0] or not parts[0][0].isdigit():
        return None  # hlavička alebo prázdny riadok
    dt, o, h, l, c, v = parts[:6]
    return dt, float(o), float(h), float(l), float(c), float(v)


#: Koľko riadkov sa vzorkuje husto, kým prejde vzorkovanie na každý `step`-tý riadok.
MIN_SAMPLE = 1000


def scale_reference(lines: Iterable[str], step: int = 1000) -> float | None:
    """Medián uzavretia: prvých `MIN_SAMPLE` riadkov celé, potom každý `step`-tý.

    Lacný prvý prechod súborom — 6 miliónov riadkov dá ~7 000 vzoriek.
    """
    sample: list[float] = []
    for i, line in enumerate(lines):
        if len(sample) >= MIN_SAMPLE and i % step:
            continue
        row = _parse(line)
        if row is not None:
            sample.append(row[4])
    if not sample:
        return None
    sample.sort()
    return sample[len(sample) // 2]


def _num(x: float) -> str:
    """Číslo bez exponentu a bez zbytočných núl: 24271.599 -> '24271.599', 0.0 -> '0'."""
    return f"{x:.12g}"


def _rescale(price: float, ref: float) -> tuple[float, bool]:
    if price > ref * SCALE_RATIO:
        return price / SCALE_FACTOR, True
    if price < ref / SCALE_RATIO:
        return price * SCALE_FACTOR, True
    return price, False


def convert_lines(
    lines: Iterable[str],
    *,
    reference: float | None,
    date_from: str | None = None,
    date_to: str | None = None,
    stamp: str = "close",
    drop_padding: bool = True,
    fix_scale: bool = False,
    date_format: str = "%Y-%m-%d",
    volume_scale: float = 1.0,
    stats: ConvertStats | None = None,
) -> Iterator[str]:
    """Jadro prevodu nad riadkami — bez súborov, aby sa dalo testovať v pamäti."""
    if stamp not in ("close", "open"):
        raise ValueError(f"stamp musí byť 'close' alebo 'open', nie {stamp!r}")
    st = stats if stats is not None else ConvertStats()
    st.reference = reference
    lo = f"{date_from} 00:00:00" if date_from else None
    hi = f"{date_to} 23:59:59" if date_to else None
    prev_close: float | None = None
    seen_days: set[str] = set()

    for line in lines:
        row = _parse(line)
        if row is None:
            continue
        st.rows_in += 1
        dt, o, h, l, c, v = row

        if reference is not None:
            o2, f1 = _rescale(o, reference)
            h2, f2 = _rescale(h, reference)
            l2, f3 = _rescale(l, reference)
            c2, f4 = _rescale(c, reference)
            if f1 or f2 or f3 or f4:
                st.scale_outliers += 1
                day = dt[:10]
                if day not in seen_days:
                    seen_days.add(day)
                    st.outlier_days.append(day)
                if fix_scale:
                    o, h, l, c = o2, h2, l2, c2
                    st.scale_fixed += 1

        # vypchávka sa posudzuje ešte pred orezaním obdobia, aby prvý bar okna
        # nebol plochý zvyšok víkendu
        is_padding = o == h == l == c and prev_close is not None and c == prev_close
        prev_close = c
        if drop_padding and is_padding:
            st.dropped_padding += 1
            continue
        if (lo and dt < lo) or (hi and dt > hi):
            st.dropped_range += 1
            continue

        t = datetime.fromisoformat(dt)
        if stamp == "close":
            t += MINUTE
        vol = int(round(v * volume_scale))
        out = f"{t.strftime(date_format)},{t.strftime('%H:%M:%S')},{_num(o)},{_num(h)},{_num(l)},{_num(c)},{vol}"
        if st.first is None:
            st.first = dt
        st.last = dt
        st.rows_out += 1
        yield out


def convert(src: Path, dst: Path, *, fix_scale: bool = False, **kw) -> ConvertStats:
    """Dva prechody súborom: referencia mierky, potom samotný prevod pre QuoteManager."""
    stats = ConvertStats()
    with open(src, encoding="utf-8") as fh:
        reference = scale_reference(fh)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, encoding="utf-8") as fh, open(dst, "w", encoding="utf-8", newline="\n") as out:
        out.write("Date,Time,Open,High,Low,Close,Volume\n")
        for line in convert_lines(fh, reference=reference, fix_scale=fix_scale, stats=stats, **kw):
            out.write(line + "\n")
    return stats


# --------------------------------------------------------------------------- #
# Cesta pre Tester: ročné feather súbory
# --------------------------------------------------------------------------- #


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


def write_years(df, stem: str, *, archive: Path = MULTICHARTS_ARCHIVE, from_year: int | None = None,
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


# --------------------------------------------------------------------------- #
# Cesta pre Freqtrade: sviečky po timeframoch
# --------------------------------------------------------------------------- #

#: Čo potrebuje IBS: graf 3m, detekčný TF 5m a 1m na `--timeframe-detail`.
FT_TIMEFRAMES = ("1m", "3m", "5m")


def write_freqtrade(df, stem: str, *, datadir: Path = DUKASCOPY_FT_DATA,
                    timeframes: Sequence[str] = FT_TIMEFRAMES, verbose: bool = True) -> list[Path]:
    """1m sviečky → `<datadir>/<STEM>-<TF>.feather` pre každý žiadaný timeframe.

    Freqtrade si vyšší TF z 1m **nedopočíta** — keď preň nemá súbor, backtest skončí na
    „No history … found". Dukascopy pritom 3m ani 5m nedodáva (a nie je to burza v ccxt,
    takže sa nedá stiahnuť), takže jediná cesta je poskladať ich tým istým pravidlom, aké
    používa emulátor MultiCharts aj graf webapp (`tools.candles.resample_ohlcv`) — inak by
    Freqtrade beh a emulátor počítali z iných barov.

    Sú to **odvodené** súbory: ležia v gitignorovanom `user_data/data/`, nikdy v archíve,
    a kedykoľvek sa dajú vyrobiť znova z 1m. Beh ich vidí cez `--datadir`.
    """
    written: list[Path] = []
    datadir.mkdir(parents=True, exist_ok=True)
    for tf in timeframes:
        minutes = int(tf.rstrip("m")) if tf.endswith("m") else int(tf.rstrip("h")) * 60
        part = resample_ohlcv(df, minutes)
        out = datadir / f"{stem}-{tf}.feather"
        part.to_feather(out)
        written.append(out)
        if verbose:
            print(f"  {out.name}  {len(part):>8} barov  {out.stat().st_size / 1e6:.1f} MB")
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
        f"Kostra vyrobena prikazom `python -m tradebot.tools.dukas_import ... --symbol {name}`.",
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
        prog="python -m tradebot.tools.dukas_import",
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("src", type=Path, help="Dukascopy CSV: dt,o,h,l,c,vol (1m, UTC)")
    ap.add_argument("--symbol", required=True,
                    help="meno symbolu (NAS100, EURUSD…) alebo kľúč inštrumentu (nas100_dukascopy)")
    ap.add_argument("--target", nargs="+", default=["tester", "multicharts"],
                    choices=("tester", "multicharts", "freqtrade", "both", "all"),
                    help="kam dáta vyrobiť; dá sa vymenovať viac (predvolene tester multicharts)")
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD, vrátane")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD, vrátane")
    ap.add_argument("--fix-scale", action="store_true", help="opraviť riadky s cenou ×1000 / ÷1000")
    ap.add_argument("--keep-padding", action="store_true", help="nevyhadzovať ploché opakované bary")

    mc = ap.add_argument_group("MultiCharts (QuoteManager)")
    mc.add_argument("--mc-out", type=Path, help="výstupný ASCII súbor (predvolene <src>_mc.csv vedľa zdroja)")
    mc.add_argument("--stamp", choices=("close", "open"), default="close",
                    help="čas baru: close = +1 min (konvencia MultiCharts), open = ako v zdroji")
    mc.add_argument("--date-format", default="%Y-%m-%d", help="strftime formát dátumu (predvolene ISO)")
    mc.add_argument("--volume-scale", type=float, default=100.0,
                    help="objem = round(vol × N); QuoteManager chce celé číslo, CFD majú loty s desatinami")

    ts = ap.add_argument_group("Tester (webapp)")
    ts.add_argument("--archive", type=Path, default=MULTICHARTS_ARCHIVE, help="kam ročné feather súbory")
    ts.add_argument("--no-merge", action="store_true", help="nezložiť pracovný súbor pre webapp")

    ft = ap.add_argument_group("Freqtrade (hyperopt, FreqAI)")
    ft.add_argument("--ft-datadir", type=Path, default=DUKASCOPY_FT_DATA,
                    help="kam sviečky po timeframoch (beh ich berie cez --datadir)")
    ft.add_argument("--ft-timeframes", nargs="+", default=list(FT_TIMEFRAMES),
                    help="ktoré timeframy poskladať z 1m")

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

    targets = set(args.target)
    if "all" in targets:
        targets |= {"tester", "multicharts", "freqtrade"}
    if "both" in targets:
        targets |= {"tester", "multicharts"}

    rc = 0
    if "multicharts" in targets:
        dst = args.mc_out or args.src.with_name(f"{args.src.stem}_mc.csv")
        stats = convert(
            args.src, dst,
            date_from=args.date_from, date_to=args.date_to, stamp=args.stamp,
            drop_padding=not args.keep_padding, fix_scale=args.fix_scale,
            date_format=args.date_format, volume_scale=args.volume_scale,
        )
        print(f"\nMultiCharts (QuoteManager): {dst}", file=err)
        print(stats.summary(), file=err)
        if stats.scale_outliers and not args.fix_scale:
            print("POZOR: subor obsahuje riadky inej mierky a neboli opravene.", file=err)
            rc = 2

    if targets & {"tester", "freqtrade"}:
        df = load_dukas_frame(args.src, drop_padding=not args.keep_padding)
        if args.date_from:
            df = df[df["date"] >= f"{args.date_from} 00:00:00+00:00"]
        if args.date_to:
            df = df[df["date"] <= f"{args.date_to} 23:59:59+00:00"]
        df = df.reset_index(drop=True)
        if df.empty:
            print("po orezani --from/--to neostal ziadny bar", file=err)
            return 1
        print(f"\n{len(df)} 1m barov {df['date'].min():%Y-%m-%d} .. "
              f"{df['date'].max():%Y-%m-%d} -> {inst.data_stem}", file=err)

        if "tester" in targets:
            print("Tester (burza MultiCharts):", file=err)
            files = write_years(df, inst.data_stem, archive=args.archive)
            print(f"zapisanych {len(files)} rocnych suborov do {args.archive} (commitni ich)", file=err)
            if not args.no_merge:
                from . import data_archive

                data_archive.merge(verbose=False, roots=((args.archive, MULTICHARTS_DATA),))
                print(f"pracovny subor: {MULTICHARTS_DATA / f'{inst.data_stem}-1m.feather'}", file=err)
            print(f"par {inst.exchange_symbol} je po restarte webapp v ponuke Novy beh", file=err)

        if "freqtrade" in targets:
            print("Freqtrade (hyperopt, FreqAI):", file=err)
            write_freqtrade(df, inst.data_stem, datadir=args.ft_datadir, timeframes=args.ft_timeframes)
            print(f"odvodene subory v {args.ft_datadir} (negituju sa, kedykolvek znova z 1m)", file=err)
            print(f"beh: --config platforms/freqtrade/config.dukascopy.json "
                  f"--datadir {args.ft_datadir} --pairs {inst.symbol}", file=err)

    return rc


if __name__ == "__main__":
    sys.exit(main())
