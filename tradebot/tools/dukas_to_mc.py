"""Prevedie Dukascopy 1m CSV (`dt,o,h,l,c,vol`) na ASCII súbor pre MultiCharts QuoteManager.

    python -m tradebot.tools.dukas_to_mc NAS100_M1_10Y.csv --from 2021-01-01
    python -m tradebot.tools.dukas_to_mc US500_M1_10Y.csv --fix-scale --out US500_mc.csv

Prečo to nejde importovať priamo:

1. **Vypchávka.** Dukascopy export má riadok pre každú minútu vrátane víkendov a
   prestávok — plochý bar `o=h=l=c` s cenou posledného uzavretia, opakovaný dookola.
   MultiCharts by ich zobral ako skutočné bary a stratégia by ich počítala do limitov
   `*MaxBars` (sú v baroch), do ATR aj do SMA objemu. Vyhadzujú sa riadky, ktoré
   nenesú žiadnu informáciu: plochý bar s cenou rovnou predchádzajúcemu uzavretiu.
   Skutočná plochá minúta (cena sa oproti minulému baru pohla a stála) ostáva.
2. **Čas baru.** Dukascopy razí bar časom OTVORENIA, MultiCharts časom ZATVORENIA.
   Predvolene sa preto k času pripočíta jedna minúta (`--stamp close`); ak import
   v QuoteManageri dostane prepínač na čas otvorenia, daj `--stamp open`.
3. **Mierka.** Niektoré exporty (US500 2015–2019) majú celé dni s cenou ×1000.
   Nástroj to nahlási vždy; opraví len s `--fix-scale` (delí/násobí 1000 podľa
   mediánu ceny v súbore).
4. **Objem.** QuoteManager berie len celé číslo, Dukascopy CFD majú objem v lotoch
   s desatinami (0.01). Objem sa preto zapisuje ako `round(vol * --volume-scale)`;
   pre CFD daj `--volume-scale 100`, inak sa väčšina barov zaokrúhli na nulu.
   Stratégia objem z týchto dát aj tak nepoužíva (inštrument má `has_real_volume=False`).

Čas v Dukascopy exporte je UTC a v QuoteManageri sa pri importe volí ako časové pásmo
súboru GMT. Výstup má hlavičku `Date,Time,Open,High,Low,Close,Volume`; dátum je
predvolene ISO (`YYYY-MM-DD`), inak `--date-format`. Súbor sa číta prúdom, takže
375 MB desaťročný export prejde bez toho, aby sa celý načítal do pamäte.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, TextIO

__all__ = ["ConvertStats", "convert", "scale_reference"]

#: Odchýlka ceny od mediánu, od ktorej je riadok "inou mierkou" (×1000 glitch).
#: Za desať rokov sa index pohne ~5×, takže 100× je bezpečne mimo.
SCALE_RATIO = 100.0
SCALE_FACTOR = 1000.0
MINUTE = timedelta(minutes=1)


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
    """Dva prechody súborom: referencia mierky, potom samotný prevod."""
    stats = ConvertStats()
    with open(src, encoding="utf-8") as fh:
        reference = scale_reference(fh)
    with open(src, encoding="utf-8") as fh, open(dst, "w", encoding="utf-8", newline="\n") as out:
        out.write("Date,Time,Open,High,Low,Close,Volume\n")
        for line in convert_lines(fh, reference=reference, fix_scale=fix_scale, stats=stats, **kw):
            out.write(line + "\n")
    return stats


def main(argv: list[str] | None = None, stderr: TextIO | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src", type=Path, help="Dukascopy CSV: dt,o,h,l,c,vol (1m, UTC)")
    ap.add_argument("--out", type=Path, help="výstup (predvolene <src>_mc.csv vedľa zdroja)")
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD, vrátane")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD, vrátane")
    ap.add_argument("--stamp", choices=("close", "open"), default="close",
                    help="čas baru vo výstupe: close = +1 min (MultiCharts konvencia), open = ako v zdroji")
    ap.add_argument("--keep-padding", action="store_true", help="nevyhadzovať ploché opakované bary")
    ap.add_argument("--fix-scale", action="store_true", help="opraviť riadky s cenou ×1000 / ÷1000")
    ap.add_argument("--date-format", default="%Y-%m-%d", help="strftime formát dátumu (predvolene ISO)")
    ap.add_argument("--volume-scale", type=float, default=1.0,
                    help="objem = round(vol × N); QuoteManager chce celé číslo, CFD majú loty s desatinami -> 100")
    args = ap.parse_args(argv)
    stderr = stderr or sys.stderr  # až tu, aby pytest capsys videl výstup

    dst = args.out or args.src.with_name(f"{args.src.stem}_mc.csv")
    stats = convert(
        args.src, dst,
        date_from=args.date_from, date_to=args.date_to, stamp=args.stamp,
        drop_padding=not args.keep_padding, fix_scale=args.fix_scale,
        date_format=args.date_format, volume_scale=args.volume_scale,
    )
    print(f"zapisane: {dst}", file=stderr)
    print(stats.summary(), file=stderr)
    if stats.scale_outliers and not args.fix_scale:
        print("POZOR: subor obsahuje riadky inej mierky a neboli opravene.", file=stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
