"""Analytika obchodov — a hlavne to, čo NESMIE tvrdiť.

Rozdelenie obchodov na skupiny je užitočné len vtedy, keď je jasné, ktorá vlastnosť sa dá
poznať **pri vstupe**. „Obchody, ktoré skončili na stope, majú zlý break-even" je pravda
a zároveň bezcenná: filter na to postaviť nejde, lebo dôvod výstupu v čase vstupu nikto
nepozná. Testy strážia práve túto hranicu — bez nej by analytika ukazovala obrovské
falošné príležitosti.
"""

from __future__ import annotations

import pytest

pytest.importorskip("freqtrade")

from tester import analytics as an
from tradebot.strategies import get_spec


def trade(*, open_rate=100.0, close_rate=101.0, amount=1.0, short=False,
          hour=10, exit_reason="roi", duration=60, hi=None, lo=None, tag="ibs:1"):
    """Obchod v tvare, aký ukladá Freqtrade do `trades.json`."""
    smer = -1.0 if short else 1.0
    return {
        "open_date": f"2025-09-04T{hour:02d}:00:00+00:00",
        "close_date": f"2025-09-04T{hour:02d}:30:00+00:00",
        "open_rate": open_rate, "close_rate": close_rate, "amount": amount,
        "profit_abs": (close_rate - open_rate) * amount * smer,
        "profit_ratio": (close_rate - open_rate) / open_rate * smer,
        "is_short": short, "exit_reason": exit_reason, "trade_duration": duration,
        "max_rate": hi if hi is not None else max(open_rate, close_rate),
        "min_rate": lo if lo is not None else min(open_rate, close_rate),
        "enter_tag": tag,
    }


# --------------------------------------------------------------------------- #
# break-even
# --------------------------------------------------------------------------- #


def test_break_even_je_hruby_zisk_na_objem():
    """Dva obchody s tým istým ziskom, ale polovičným objemom, majú dvojnásobný break-even."""
    velky = [trade(open_rate=100, close_rate=101, amount=10)]
    maly = [trade(open_rate=100, close_rate=101, amount=5)]
    assert an.break_even_pct(velky) == pytest.approx(0.4975, abs=1e-4)
    assert an.break_even_pct(maly) == an.break_even_pct(velky)   # podiel je rovnaký

    # …a pri rovnakom objeme rozhoduje zisk
    lepsi = [trade(open_rate=100, close_rate=102, amount=10)]
    assert an.break_even_pct(lepsi) > an.break_even_pct(velky)


def test_short_sa_pocita_opacne():
    assert an.break_even_pct([trade(open_rate=100, close_rate=99, short=True)]) > 0
    assert an.break_even_pct([trade(open_rate=100, close_rate=101, short=True)]) < 0


def test_bez_objemu_je_break_even_nedefinovany():
    assert an.break_even_pct([]) is None
    assert an.break_even_pct([trade(amount=0.0)]) is None


# --------------------------------------------------------------------------- #
# hranica medzi filtrom a pohľadom dozadu
# --------------------------------------------------------------------------- #


def test_vysledkove_vlastnosti_su_oznacene_a_nie_su_v_prilezitostiach():
    """Toto je ten podstatný test: `exit_reason` sa v čase vstupu nedá poznať.

    Keby bol medzi príležitosťami, obsadil by prvé miesta (obchody na TP majú
    samozrejme lepší break-even než tie na stope) a vyzeralo by to ako obrovská
    príležitosť, hoci je to len pohľad dozadu.
    """
    obchody = ([trade(close_rate=102, exit_reason="roi", hour=9, duration=30 + i,
                      short=i % 2 == 0) for i in range(20)]
               + [trade(close_rate=98, exit_reason="stop_loss", hour=14, duration=90 + i,
                        short=i % 2 == 0) for i in range(20)])
    report = an.analyze(obchody, strategy="ibs", min_bucket=5)

    vopred = {s["feature"] for s in report["splits"]}
    potom = {s["feature"] for s in report["descriptive"]}
    assert "exit_reason" in potom and "exit_reason" not in vopred
    assert {"mae_pct", "mfe_pct", "duration_min"} <= potom
    assert "hour" in vopred and "direction" in vopred
    assert all(s["at_entry"] for s in report["splits"])
    assert not any(s["at_entry"] for s in report["descriptive"])


def test_headline_pri_vyrovnanom_behu_hovori_ze_nie_je_co_filtrovat():
    """Keď žiadna skupina nevyčnieva, model nemá čo nájsť — a treba to povedať."""
    # Každá hodina má presne tú istú zmes — inak by korelácia vznikla len z toho,
    # ako fixtúra strieda hodnoty.
    obchody = []
    for hodina in range(8, 14):
        obchody += [trade(close_rate=101, hour=hodina, duration=40 + i) for i in range(5)]
        obchody += [trade(close_rate=99, hour=hodina, duration=40 + i) for i in range(5)]
    report = an.analyze(obchody, strategy="ibs", min_bucket=5)
    assert "nema co najst" in report["headline"], report["headline"]


def test_headline_pri_velkej_skupine_hovori_o_parametri_nie_o_filtri():
    """Odfiltrovať 90 % obchodov nie je filter, je to iná stratégia."""
    obchody = ([trade(close_rate=99.5, hour=9) for _ in range(54)]
               + [trade(close_rate=105, hour=15) for _ in range(6)])
    report = an.analyze(obchody, strategy="ibs", min_bucket=5)
    assert "VACSINA" in report["headline"]


# --------------------------------------------------------------------------- #
# skupiny
# --------------------------------------------------------------------------- #


def test_cisla_sa_delia_na_rovnako_velke_skupiny():
    """Rovnako široké intervaly by pri zošikmenom rozdelení dali jednu skupinu so všetkým."""
    obchody = [trade(duration=d) for d in ([5] * 30 + [1000] * 10)]
    rozdelenie = an.split(obchody, next(f for f in an.FEATURES if f.key == "duration_min"),
                          quantiles=2, min_bucket=5)
    assert rozdelenie is not None
    assert sorted(b.trades for b in rozdelenie.buckets) == [10, 30]


def test_male_skupiny_vypadnu():
    """Päť obchodov o skupine nič nehovorí — číslo by bolo šum."""
    obchody = [trade(hour=9) for _ in range(30)] + [trade(hour=23) for _ in range(3)]
    rozdelenie = an.split(obchody, next(f for f in an.FEATURES if f.key == "weekday"),
                          min_bucket=8)
    assert rozdelenie is None          # všetko je jeden deň, druhá skupina neexistuje


def test_vlastnost_s_jednou_hodnotou_nie_je_rozdelenie():
    obchody = [trade(short=False) for _ in range(40)]
    rozdelenie = an.split(obchody, next(f for f in an.FEATURES if f.key == "direction"))
    assert rozdelenie is None


def test_zmena_je_break_even_zvysku_minus_celok():
    obchody = ([trade(close_rate=99, hour=9) for _ in range(20)]
               + [trade(close_rate=103, hour=15) for _ in range(20)])
    rozdelenie = an.split(obchody, next(f for f in an.FEATURES if f.key == "hour"),
                          quantiles=2, min_bucket=5)
    najhorsia = rozdelenie.buckets[0]
    celok = an.break_even_pct(obchody)

    assert najhorsia.break_even_pct < celok
    assert najhorsia.impact == pytest.approx(najhorsia.without_pct - celok, abs=1e-4)
    assert najhorsia.impact > 0          # bez stratovej skupiny by bol beh lepší


# --------------------------------------------------------------------------- #
# čo vie len stratégia
# --------------------------------------------------------------------------- #


def test_vzdialenost_stopu_sa_berie_z_kresieb_strategie():
    """`trades.json` má len to, čo Freqtrade urobil; plán obchodu je v kresbách."""
    obchody = [trade(tag="ibs:1000")]
    chart = {"objects": [
        {"k": "sl_box", "x1": 1000, "y1": 100.0, "y2": 99.0},
        {"k": "tp_box", "x1": 1000, "y1": 100.0, "y2": 103.0},
    ]}
    an.enrich(obchody, chart, "ibs")

    assert obchody[0]["_sl_pct"] == pytest.approx(1.0)      # 1 bod na cene 100
    assert obchody[0]["_rr_planned"] == pytest.approx(3.0)  # TP 3 body, SL 1 bod


def test_bez_kresieb_vlastnosti_planu_jednoducho_nie_su():
    obchody = [trade()]
    an.enrich(obchody, None, "ibs")
    assert "_sl_pct" not in obchody[0]
    kluce = {f.key for f in an.features_for("demo_breakout")}
    assert "sl_pct" not in kluce        # stratégia bez `sl_kind` tú vlastnosť nemá


def test_ktory_parameter_vlastnost_riadi_vie_strategia():
    """Analytika nekončí zistením, ale odkazom na to, čo sa dá preladiť."""
    obchody = ([trade(close_rate=99, hour=9) for _ in range(20)]
               + [trade(close_rate=103, hour=15) for _ in range(20)])
    report = an.analyze(obchody, strategy="ibs", min_bucket=5)
    podla_mena = {s["feature"]: s for s in report["splits"]}

    assert podla_mena["hour"]["param"] == "sess2TradeStartH"
    assert "sess2TradeStartH" in report["tunable"]
    # Stratégia bez mapovania nedostane odkaz na parameter, ale rozdelenie áno.
    demo = an.analyze(obchody, strategy="demo_breakout", min_bucket=5)
    assert demo["splits"] and all(s["param"] is None for s in demo["splits"])


def test_odkazovane_parametre_naozaj_existuju():
    """Regresia: preklep vo `FEATURE_PARAMS` by dal tlačidlo, ktoré nič nenachystá."""
    from dataclasses import fields

    from tradebot.adapters.freqtrade.hyperplan import knowledge

    for key in ("ibs", "demo_breakout"):
        spec = get_spec(key)
        polia = {f.name for f in fields(spec.config_cls)}
        vlastnosti = {f.key for f in an.features_for(key)}
        for feature, param in knowledge(spec).FEATURE_PARAMS.items():
            assert param in polia, f"{key}: {param!r} nie je pole configu"
            assert feature in vlastnosti, f"{key}: {feature!r} nie je vlastnosť obchodu"
