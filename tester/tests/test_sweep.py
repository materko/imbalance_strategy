"""Sweep — rozbalenie mriežky a výber podľa kritéria (`tester.sweep`).

Kritérium je to, čo z mriežky robí odpoveď: „najvyšší winrate pri drawdowne do 15 %" je
niečo iné než „najvyšší zisk pri tom istom limite". Testy strážia obe časti: že sa hodnoty
rozbalia tak, ako ich tester napísal, a že poradie zodpovedá zadaniu.
"""

from __future__ import annotations

import pytest

from tester import sweep


def run(name_values: dict, *, trades=50, pnl=10.0, wr=50.0, dd=5.0, be=0.1, status="done"):
    """Záznam behu v tvare, aký ukladá `RunStore`."""
    return {
        "id": "x", "status": status,
        "settings": {"sweep": {"id": "s1", "values": name_values}},
        "result": {"trades": trades, "pnl_pct": pnl, "winrate": wr,
                   "max_drawdown_pct": dd, "break_even_pct": be},
    }


# --------------------------------------------------------------------------- #
# hodnoty a mriežka
# --------------------------------------------------------------------------- #


def test_rozsah_vratane_hornej_hranice():
    assert sweep.parse_values("2:6:1") == [2, 3, 4, 5, 6]
    assert sweep.parse_values("1:2:0.5") == [1.0, 1.5, 2.0]


def test_zoznam_hodnot_aj_s_typmi():
    assert sweep.parse_values("3,5,8") == [3, 5, 8]
    assert sweep.parse_values("true,false") == [True, False]
    assert sweep.parse_values("Long only,Both") == ["Long only", "Both"]
    assert sweep.parse_values("0.25@pct") == [{"value": 0.25, "unit": "pct"}]


def test_pokazeny_rozsah_sa_ohlasi():
    for bad in ("2:6", "2:6:0", "2:6:-1"):
        with pytest.raises(ValueError):
            sweep.parse_values(bad)


def test_mriezka_je_kartezsky_sucin():
    points = sweep.expand({"a": [1, 2], "b": ["x", "y"]})
    assert points == [{"a": 1, "b": "x"}, {"a": 1, "b": "y"},
                      {"a": 2, "b": "x"}, {"a": 2, "b": "y"}]


def test_parameter_bez_hodnot_je_chyba():
    with pytest.raises(ValueError, match="hodnoty"):
        sweep.expand({"a": []})


# --------------------------------------------------------------------------- #
# kritériá
# --------------------------------------------------------------------------- #


def test_break_even_je_predvolene_kriterium():
    rows = [run({"rr": 2}, be=0.10), run({"rr": 5}, be=0.17), run({"rr": 3}, be=0.12)]
    assert [r["settings"]["sweep"]["values"]["rr"] for r in sweep.rank(rows)] == [5, 3, 2]


def test_winrate_pri_strope_na_drawdown():
    """Najvyšší winrate má beh, ktorý prekračuje limit — ten sa nesmie stať víťazom."""
    rows = [run({"rr": 2}, wr=70.0, dd=30.0), run({"rr": 3}, wr=60.0, dd=10.0),
            run({"rr": 4}, wr=55.0, dd=8.0)]
    ranked = sweep.rank(rows, "winrate", max_dd=15.0)

    assert [r["settings"]["sweep"]["values"]["rr"] for r in ranked] == [3, 4, 2]
    assert ranked[0]["sweep_ok"] and ranked[-1]["sweep_why"] == "drawdown 30.0 % > 15 %"


def test_zisk_neriesi_winrate_ale_limit_drawdownu_ano():
    rows = [run({"rr": 2}, pnl=40.0, wr=30.0, dd=25.0), run({"rr": 3}, pnl=20.0, wr=30.0, dd=12.0)]
    ranked = sweep.rank(rows, "profit", max_dd=20.0)
    assert ranked[0]["settings"]["sweep"]["values"]["rr"] == 3
    assert not ranked[1]["sweep_ok"]


def test_drawdown_sa_minimalizuje():
    rows = [run({"rr": 2}, dd=9.0), run({"rr": 3}, dd=4.0), run({"rr": 4}, dd=6.0)]
    assert [r["settings"]["sweep"]["values"]["rr"] for r in sweep.rank(rows, "drawdown")] == [3, 4, 2]


def test_malo_obchodov_a_nedobehnute_behy_su_mimo():
    rows = [run({"rr": 2}, trades=5, be=0.9), run({"rr": 3}, trades=60, be=0.2),
            run({"rr": 4}, status="failed"), run({"rr": 5}, trades=0)]
    ranked = sweep.rank(rows, min_trades=20)

    assert ranked[0]["settings"]["sweep"]["values"]["rr"] == 3
    dovody = {r["settings"]["sweep"]["values"]["rr"]: r["sweep_why"] for r in ranked if not r["sweep_ok"]}
    assert dovody == {2: "< 20 obchodov", 4: "failed", 5: "0 obchodov"}


def test_neznam_kriterium_sa_ohlasi():
    with pytest.raises(ValueError, match="kritérium"):
        sweep.rank([], "nieco")


# --------------------------------------------------------------------------- #
# výpis
# --------------------------------------------------------------------------- #


def test_zadanie_sa_da_precitat_ako_veta():
    assert sweep.describe("winrate", 15.0, 20) == \
        "najvyšší podiel ziskových pri drawdown ≤ 15 % a ≥ 20 obchodov"
    assert sweep.describe("profit", None, None) == "najvyšší zisk"


def test_tabulka_oznaci_najlepsi_a_dovod_vyradenia():
    rows = sweep.rank([run({"rr": 5}, be=0.2), run({"rr": 2}, be=0.9, dd=40.0)], max_dd=10.0)
    text = sweep.table(rows, ["rr"])

    assert text.encode("ascii", "replace")            # konzola na Windows
    assert "<- najlepsi" in text.splitlines()[2]
    assert "drawdown 40.0 % > 10 %" in text


def test_parametre_lamuce_paritu_su_oznacene():
    """Ladiť sa dajú, ale tester má vedieť, že výsledok sa už nedá porovnať s Pine."""
    from tester.webapp.param_meta import param_metadata

    by_name = {m["name"]: m for m in param_metadata("ibs")}
    assert by_name["legacyPineSizing"]["breaks_parity"] and by_name["state2MaxBars"]["breaks_parity"]
    assert not by_name["rrRatio"]["breaks_parity"]


def test_velkostny_zoznam_je_pre_hyperopt_zoznam_moznosti():
    """`0.1@pct,0.5@pct` sú dve možnosti, nie rozsah — ako každý vypísaný zoznam."""
    knob = sweep.to_knob("0.1@pct,0.5@pct")
    assert "choices" in knob and len(knob["choices"]) == 2
    assert knob["choices"][0] == {"value": 0.1, "unit": "pct"}


def test_min_trades_plati_na_rok_a_prepocita_sa_na_okno():
    rok = {"status": "done", "settings": {"timerange": "20250904-20260904"},
           "result": {"trades": 40, "break_even_pct": 0.1}}
    stvrtrok = {"status": "done", "settings": {"timerange": "20250904-20251204"},
                "result": {"trades": 20, "break_even_pct": 0.1}}
    assert sweep.required_trades(60, rok) == 60
    assert sweep.required_trades(60, stvrtrok) == 14
    assert sweep.rank([rok], min_trades=60)[0]["sweep_ok"] is False
    assert sweep.rank([stvrtrok], min_trades=60)[0]["sweep_ok"] is True
