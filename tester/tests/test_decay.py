"""Slabne edge? — test proti vlastnej minulosti.

Testy stoja na trhoch, ktorých priebeh poznáme dopredu: buď je edge po celý čas rovnaký,
alebo v poslednej štvrtine zmizne. Zmyslom je strážiť, že sa jedno od druhého odlíši —
a hlavne že sa referenčné rozdelenie ťahá z **celej** histórie, nie z testovaného úseku.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("numpy")

from tester import decay as dc

ZACIATOK = datetime(2024, 1, 1, tzinfo=timezone.utc)


def obchod(poradie: int, *, vyhra: bool, krok_hodin: float = 4.0) -> dict:
    """Obchod s pevným ziskom alebo stratou; break-even je z cien, nie z `profit_abs`."""
    cas = ZACIATOK + timedelta(hours=krok_hodin * poradie)
    close = 101.0 if vyhra else 99.0
    return {"open_date": cas.isoformat(), "open_rate": 100.0, "close_rate": close,
            "amount": 1.0, "is_short": False,
            "profit_abs": 1.0 if vyhra else -1.0}


def seria(vzor, pocet: int, **kw) -> list[dict]:
    """`vzor(i) -> bool` rozhoduje, či je i-ty obchod výhra."""
    return [obchod(i, vyhra=vzor(i), **kw) for i in range(pocet)]


# --------------------------------------------------------------------------- #
# rozpozná stabilný edge od dohoreného
# --------------------------------------------------------------------------- #


def test_rovnomerny_edge_drzi():
    """Dve výhry na jednu stratu po celý čas — posledné obdobie nie je ničím zvláštne."""
    v = dc.analyze(seria(lambda i: i % 3 != 2, 240), iterations=400)

    assert v.verdict == "DRZI"
    assert len(v.periods) == 4
    assert 15 < v.last.percentile < 85


def test_dohoreny_edge_sa_ohlasi():
    """Prvé tri štvrtiny zarábajú, posledná už len stráca."""
    trades = seria(lambda i: i < 180 and i % 3 != 2, 240)
    v = dc.analyze(trades, iterations=400)

    assert v.verdict == "SLABNE"
    assert v.last.percentile < 5
    assert v.last.break_even_pct < 0
    assert "regime" in v.note  # rada overit rezim trhu, nez sa strategia vypne


def test_zosilneny_edge_sa_tiez_ohlasi():
    """Opačný prípad — a výpis musí varovať pred zvyšovaním rizika."""
    trades = seria(lambda i: i >= 180 or i % 3 == 2, 240)
    v = dc.analyze(trades, iterations=400)

    assert v.verdict == "ZLEPSUJE SA"
    assert "riziko" in v.note


# --------------------------------------------------------------------------- #
# referenčné rozdelenie
# --------------------------------------------------------------------------- #


def test_vzorky_sa_tahaju_z_CELEJ_historie():
    """Toto je jadro testu: krátky úsek sa porovnáva s dlhou minulosťou.

    Prvá verzia losovala indexy len do veľkosti vzorky, takže sa referenčné rozdelenie
    počítalo z prvých dvadsiatich obchodov histórie — teda z niečoho úplne iného, než
    z čoho malo.
    """
    import numpy as np

    rng = np.random.default_rng(0)
    idx = dc._draw(rng, 200, pop=500, size=20, block=1)

    assert idx.shape == (200, 20)
    assert idx.max() > 20          # siaha za dlzku vzorky
    assert idx.max() < 500


def test_blok_drzi_obchody_pokope():
    import numpy as np

    rng = np.random.default_rng(0)
    idx = dc._draw(rng, 50, pop=500, size=20, block=5)
    rozdiely = np.diff(idx, axis=1)

    # V bloku ide index o jeden hore; zlom je len na hraniciach blokov.
    assert (rozdiely == 1).mean() > 0.7


# --------------------------------------------------------------------------- #
# delenie na obdobia
# --------------------------------------------------------------------------- #


def test_ziadny_obchod_sa_pri_deleni_nestrati():
    trades = seria(lambda i: i % 2 == 0, 240)
    v = dc.analyze(trades, iterations=200)

    assert sum(p.trades for p in v.periods) == len(trades)


def test_delenie_podla_poctu_da_rovnako_velke_obdobia():
    """Pre riedke obchody, kde by kalendárny úsek ostal poloprázdny."""
    trades = seria(lambda i: i % 3 != 2, 200)
    v = dc.analyze(trades, by="count", parts=4, iterations=200)

    assert [p.trades for p in v.periods] == [50, 50, 50, 50]


def test_kalendarne_delenie_ukaze_riedke_obdobie():
    """Obchody, ktoré v druhej polovici zredli — kalendárne delenie to musí ukázať."""
    husto = [obchod(i, vyhra=i % 3 != 2) for i in range(180)]
    riedko = [obchod(180 + i * 12, vyhra=i % 3 != 2) for i in range(30)]
    v = dc.analyze(husto + riedko, iterations=300)

    assert v.periods[0].per_month > v.periods[-1].per_month * 2
    assert "Signálov" in v.note


# --------------------------------------------------------------------------- #
# málo dát
# --------------------------------------------------------------------------- #


def test_malo_obchodov_nedostane_verdikt():
    """Radšej „málo dát“ než číslo, ktoré nič neznamená."""
    v = dc.analyze(seria(lambda i: i % 3 != 2, 20), iterations=200)

    assert v.verdict == "MALO DAT"
    assert v.lo is None
    assert len(v.periods) == 4          # obdobia sa aj tak vypisu, len sa nehodnotia


def test_obchody_bez_datumu_sa_preskocia():
    trades = seria(lambda i: i % 3 != 2, 120) + [{"open_date": "", "open_rate": 100.0,
                                                  "close_rate": 101.0, "amount": 1.0}]
    v = dc.analyze(trades, iterations=200)

    assert v.trades == 120


# --------------------------------------------------------------------------- #
# verdikt nad hotovými číslami
# --------------------------------------------------------------------------- #


def obdobie(be: float, percentil: float | None = None, obchodov: int = 50) -> dc.Period:
    return dc.Period(label="x", start="", end="", trades=obchodov, break_even_pct=be,
                     winrate=50.0, per_month=10.0, percentile=percentil)


def test_klesajuci_rad_dostane_varovanie_aj_ked_je_posledne_v_medziach():
    """Rad, ktorý klesá po celý čas, je silnejší signál než jedno slabé obdobie."""
    d = dc.Decay(periods=[obdobie(0.09), obdobie(0.07), obdobie(0.05), obdobie(0.03, 30.0)],
                 trades=200, lo=-0.02, hi=0.12, median=0.05, sd=0.04, slope=-0.02)
    znacka, veta = dc._verdict(d, dc.CONF)

    assert znacka == "POZOR NA TREND"
    assert "30. percentil" in veta


def test_jedno_slabe_obdobie_uprostred_verdikt_nemeni():
    d = dc.Decay(periods=[obdobie(0.09), obdobie(-0.05), obdobie(0.07), obdobie(0.06, 55.0)],
                 trades=200, lo=-0.02, hi=0.12, median=0.05, sd=0.04, slope=0.0)
    znacka, _ = dc._verdict(d, dc.CONF)

    assert znacka == "DRZI"


def test_vypis_ma_kazde_obdobie_na_vlastnom_riadku():
    v = dc.analyze(seria(lambda i: i % 3 != 2, 240), iterations=200)
    text = dc.report(v, "TEST/USD")

    assert "TEST/USD" in text
    for p in v.periods:
        assert p.label in text
