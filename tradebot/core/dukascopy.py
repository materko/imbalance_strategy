"""Surový Dukascopy 1m export — čítanie riadku a pravidlo vypchávky.

Patrí do jadra, lebo z toho istého súboru číta **MultiCharts študia**, keď jej beta
nedá Data2 (`adapters/multicharts/htf_csv.py`) — teda produkt, nie Tester. Import dát
v Testeri (`tester/dukas_import.py`) používa tie isté dve funkcie, takže surový export
sa všade interpretuje rovnako.

Formát: `dt,o,h,l,c,vol`, čas **otvorenia** baru v UTC, bid strana bez spreadu,
objem v lotoch s desatinami.

Bez závislostí — beží aj v tom Pythone, ktorý volá MultiCharts.
"""

from __future__ import annotations

__all__ = ["parse_line", "is_padding"]


def parse_line(line: str) -> tuple[str, float, float, float, float, float] | None:
    """`dt,o,h,l,c,vol` → n-tica, alebo `None` pre hlavičku a prázdny riadok."""
    parts = line.rstrip("\r\n").split(",")
    if len(parts) < 6 or not parts[0] or not parts[0][0].isdigit():
        return None
    dt, o, h, l, c, v = parts[:6]
    return dt, float(o), float(h), float(l), float(c), float(v)


def is_padding(o: float, h: float, l: float, c: float, prev_close: float | None) -> bool:
    """Vypchávka: plochý bar s cenou predchádzajúceho uzavretia.

    Dukascopy má riadok pre každú minútu vrátane víkendov a prestávok (~40 % súboru).
    Taký bar nenesie informáciu, ale stratégia by ho počítala do limitov `*MaxBars`
    (sú v baroch), do ATR aj do SMA objemu. Skutočná plochá minúta — cena sa oproti
    minulému baru pohla a stála — vypchávka **nie je** a ostáva.
    """
    return o == h == l == c and prev_close is not None and c == prev_close
