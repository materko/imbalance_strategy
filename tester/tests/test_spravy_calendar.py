"""Kalendár stratégie SPRÁVY: koniec pokrytia nesmie prísť potichu (audit 9. 11. 2026, M-CORE-3).

Engine koniec kalendára nepozná — po poslednom dátume typu žiadnu správu nevidí a stratégia ju naživo prestane
obchodovať bez jedinej chyby. Úrady zverejňujú termíny na ďalší rok postupne, takže každý typ končí inokedy.
"""

from __future__ import annotations

import warnings
from datetime import date, datetime

from tradebot.strategies.spravy import calendar as cal


def test_coverage_v_subore_sedi_s_poslednymi_datumami():
    """`coverage.to` je pre človeka; nesmie tvrdiť iné, než čo v dátumoch naozaj je."""
    last = cal.last_dates()
    assert set(last) == set(cal.TYPES)
    assert {t: d.isoformat() for t, d in last.items()} == cal.load()["coverage"]["to"]


def test_coverage_gaps_najde_typy_ktorym_kalendar_konci():
    last = cal.last_dates()
    prvy = min(last.values())
    # deň po konci najkratšieho typu: ten (a všetky s rovnakým koncom) už skončil
    den_po = date.fromordinal(prvy.toordinal() + 1)
    skoncene = {t for t, d in last.items() if d == prvy}
    assert {t for t, _ in cal.coverage_gaps(den_po, days=0)} == skoncene
    # dávno pred koncom nič nehlási; s dlhým výhľadom hlási všetko
    assert cal.coverage_gaps(date(2021, 6, 1), days=45) == []
    assert {t for t, _ in cal.coverage_gaps(max(last.values()), days=45)} == set(cal.TYPES)
    # hranica: posledný deň je ešte pokrytý, deň po ňom nie
    typ = next(iter(skoncene))
    assert typ not in {t for t, _ in cal.coverage_gaps(prvy, days=0)}
    assert (typ, prvy) in cal.coverage_gaps(den_po, days=0)


def test_kalendar_este_neskoncil():
    """Tvrdo padne až vtedy, keď niektorému typu kalendár **už skončil** — vtedy ho stratégia naživo neobchoduje.
    Blížiaci sa koniec (do 45 dní) je varovanie v súhrne testov: termíny treba doplniť z oficiálnych rozvrhov
    (zdroj je pri type v `calendar.json`) a vygenerovať `SpravyCalendar.cs` (`calendar --cs`)."""
    dnes = datetime.now(cal.NY).date()
    skoncene = cal.coverage_gaps(dnes, days=0)
    blizko = [g for g in cal.coverage_gaps(dnes, days=45) if g not in skoncene]
    if blizko:
        warnings.warn("kalendár SPRÁVY končí do 45 dní: " + ", ".join(f"{t} {d}" for t, d in blizko)
                      + " — doplň termíny (python -m tradebot.strategies.spravy.calendar --check)", stacklevel=1)
    assert not skoncene, ("kalendár SPRÁVY už skončil pre: " + ", ".join(f"{t} (posledný {d})" for t, d in skoncene)
                          + " — tieto správy sa naživo neobchodujú, doplň termíny do calendar.json")
