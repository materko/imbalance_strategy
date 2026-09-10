"""Monte Carlo nad hotovým behom — `tester.montecarlo`."""

from __future__ import annotations

import json
import math

import pytest

from tester import montecarlo as mc


def trade(open_rate: float, close_rate: float, amount: float = 1.0, short: bool = False) -> dict:
    return {"open_rate": open_rate, "close_rate": close_rate, "amount": amount, "is_short": short}


#: Štyri ziskové, jeden stratový — hrubý zisk 30, objem 4*(100+110) + (100+90) = 1030.
SAMPLE = [trade(100, 110), trade(100, 110), trade(100, 110), trade(100, 110), trade(100, 90)]


def test_per_trade_pocita_hruby_zisk_z_cien_nie_z_profit_abs():
    gross, volume = mc.per_trade([trade(100, 110), trade(100, 90, short=True)])
    assert list(gross) == [10.0, 10.0]           # short na klesajúcej cene zarába
    assert list(volume) == [210.0, 190.0]        # vstup + výstup


def test_per_trade_odmietne_prazdny_beh():
    with pytest.raises(ValueError, match="obchody"):
        mc.per_trade([])


def test_break_even_median_sedi_s_namieranym():
    r = mc.analyze(SAMPLE, fee_pct=0.0, iterations=2000, seed=0)
    be = r["break_even"]
    assert be["observed"] == pytest.approx(30.0 / 1030.0 * 100.0)
    assert be["lo"] < be["median"] < be["hi"]
    # medián bootstrapu sa od nameraného nemá systematicky líšiť
    assert be["median"] == pytest.approx(be["observed"], rel=0.15)


def test_interval_sa_zuzuje_s_poctom_obchodov():
    maly = mc.analyze(SAMPLE, iterations=2000, seed=0)["break_even"]
    velky = mc.analyze(SAMPLE * 20, iterations=2000, seed=0)["break_even"]
    assert (velky["hi"] - velky["lo"]) < (maly["hi"] - maly["lo"]) / 3


def test_p_above_fee_je_ta_ista_udalost_ako_zisk_nad_nulou():
    r = mc.analyze(SAMPLE * 6, fee_pct=1.0, iterations=2000, seed=1)
    assert r["break_even"]["p_above_fee"] == pytest.approx(r["net"]["p_positive"])


def test_poplatok_znizuje_cisty_zisk_o_objem_krat_sadzba():
    bez = mc.analyze(SAMPLE, fee_pct=0.0, iterations=500, seed=0)["net"]["observed"]
    s_fee = mc.analyze(SAMPLE, fee_pct=0.05, iterations=500, seed=0)["net"]["observed"]
    assert s_fee == pytest.approx(bez - 1030.0 * 0.0005)


def test_drawdown_pocita_vrchol_od_startovacieho_zostatku():
    """Prvý obchod v strate je drawdown, hoci pred ním nie je žiadny vrchol."""
    r = mc.analyze([trade(100, 90), trade(100, 110)], iterations=200, seed=0, account=1000.0)
    assert r["account"]["drawdown_abs"]["observed"] == pytest.approx(10.0)
    assert r["account"]["drawdown_pct"]["observed"] == pytest.approx(1.0)   # % z vrcholu


def test_horsie_poradie_da_hlbsi_drawdown_nez_namerane():
    dd = mc.analyze(SAMPLE * 4, iterations=2000, seed=0)["account"]["drawdown_abs"]
    assert dd["max"] > dd["observed"]        # existuje horšia postupnosť tých istých obchodov
    assert dd["median"] > 0


def test_seed_robi_vysledok_zopakovatelnym():
    a = mc.analyze(SAMPLE, iterations=500, seed=7)
    b = mc.analyze(SAMPLE, iterations=500, seed=7)
    assert a == b
    assert mc.analyze(SAMPLE, iterations=500, seed=8) != a


def test_chunkovanie_nemeni_pocet_opakovani(monkeypatch):
    monkeypatch.setattr(mc, "_CHUNK_CELLS", 30)   # vynúti niekoľko dávok
    assert sum(mc._chunks(1000, 5)) == 1000
    r = mc.analyze(SAMPLE, iterations=1000, seed=0)
    assert r["iterations"] == 1000


def test_vypis_je_ciste_ascii_a_varuje_pri_malej_vzorke():
    text = mc.report(mc.analyze(SAMPLE, fee_pct=0.05, iterations=500, seed=0), "beh", "USD")
    text.encode("ascii")                          # Windows konzola v systémovej kódovej stránke
    assert f"pod hranicou {mc.MIN_TRADES}" in text
    assert "preoptimalizovanie" in text


def test_vypis_nevarije_pri_dostatocnej_vzorke():
    text = mc.report(mc.analyze(SAMPLE * 10, fee_pct=0.05, iterations=500, seed=0), "beh")
    assert "pod hranicou" not in text



# --------------------------------------------------------------------------- #
# Účet: riziko, hranice, ruina
# --------------------------------------------------------------------------- #


def test_blok_drzi_serie_strat_pokope():
    """Blokový bootstrap musí dať dlhšie série strát než losovanie obchod po obchode."""
    trades = [trade(100, 90)] * 8 + [trade(100, 110)] * 24     # straty pokope v origináli
    iid = mc.analyze(trades, iterations=2000, seed=0, block=1)["account"]["losing_streak"]
    blok = mc.analyze(trades, iterations=2000, seed=0, block=6)["account"]["losing_streak"]
    assert blok["median"] > iid["median"]


def test_blok_sa_skrati_na_kratkej_vzorke():
    assert mc.block_size(10, 161) == 10
    assert mc.block_size(10, 12) == 2        # z 12 obchodov by blok 10 nelosoval takmer nič
    assert mc.block_size(1, 161) == 1


def test_riziko_skaluje_drawdown_lineárne():
    kw = dict(iterations=1000, seed=0, account=100_000.0, risk_ref=100.0)
    maly = mc.analyze(SAMPLE * 8, risk=100.0, **kw)["account"]
    velky = mc.analyze(SAMPLE * 8, risk=300.0, **kw)["account"]
    assert velky["drawdown_abs"]["median"] == pytest.approx(3 * maly["drawdown_abs"]["median"])
    assert velky["risk"] == 300.0 and maly["risk"] == 100.0
    # odporúčanie je vlastnosť stratégie a účtu, nie práve zvoleného rizika
    assert velky["advice"]["risk"] == pytest.approx(maly["advice"]["risk"], rel=1e-6)


def test_hranice_a_ruina_su_z_najnizsieho_bodu():
    """Samé straty (40 x -10) na účte 300: padne cez každú hranicu a skončí na nule, nie v mínuse."""
    trades = [trade(100, 90)] * 40
    acc = mc.analyze(trades, iterations=500, seed=0, account=300.0, risk_ref=10.0, risk=10.0)["account"]
    assert [round(h["p"], 3) for h in acc["hits"]] == [1.0, 1.0, 1.0, 1.0]
    assert acc["p_ruin"] == 1.0
    assert acc["drawdown_pct"]["max"] == pytest.approx(100.0)
    assert acc["final_pct"]["median"] == pytest.approx(-100.0)


def test_ziskova_seria_nema_ruinu_ani_hlboky_pokles():
    acc = mc.analyze([trade(100, 110)] * 40, iterations=500, seed=0, account=1000.0)["account"]
    assert acc["p_ruin"] == 0.0
    assert all(h["p"] == 0.0 for h in acc["hits"])
    assert acc["wait_for_high"]["max"] == 0        # každý obchod je nové maximum


#: Obchody so spojito rozptýlenými veľkosťami. Na percentily nestačí pár celých čísel:
#: rovnaké hodnoty sa zhlukujú a `P(x >= p95)` potom vyjde 10 % namiesto 5 %.
VARIED = [trade(100.0, 100.0 + round(math.sin(i * 1.7) * 13 + 1.9, 4)) for i in range(60)]


def test_odporucane_riziko_drzi_95_percent_ciest_nad_hranicou():
    kw = dict(iterations=4000, seed=0, account=10_000.0, risk_ref=100.0, limits=(10.0, 20.0))
    advice = mc.analyze(VARIED, risk=100.0, **kw)["account"]["advice"]
    assert advice["limit"] == 20.0
    # pri odporúčanom riziku má hranicu -20 % preraziť práve tých 5 % ciest
    over = mc.analyze(VARIED, risk=advice["risk"], **kw)["account"]
    hit20 = next(h for h in over["hits"] if h["limit"] == 20.0)
    assert hit20["p"] == pytest.approx(0.05, abs=0.015)


def test_zlozene_urocenie_nepusti_ucet_na_nulu():
    """Pri % z equity sa riskuje stále menej, takže séria strát účet nevynuluje."""
    trades = [trade(100, 90)] * 40
    acc = mc.analyze(trades, iterations=300, seed=0, account=1000.0,
                     risk_ref=10.0, risk_pct=2.0)["account"]
    assert acc["risk_pct"] == 2.0 and acc["p_ruin"] == 0.0
    assert acc["advice"] is None                  # linearita v riziku tu neplatí


def test_bez_dolaroveho_rizika_sa_neskaluje():
    """Profil s pevným počtom kontraktov sa premiešať dá, prepočítať na iný účet nie."""
    acc = mc.analyze(SAMPLE, iterations=300, seed=0, risk=250.0)["account"]
    assert acc["scalable"] is False and acc["risk"] is None and acc["advice"] is None


def test_sizing_of_cita_profil_behu():
    assert mc.sizing_of({"params": {"maxLossDollar": 100.0, "legacyPineSizing": False}}) == 100.0
    assert mc.sizing_of({"params": {"maxLossDollar": 100.0, "legacyPineSizing": True}}) is None
    assert mc.sizing_of({"params": {}}) is None


def test_sizing_of_berie_meno_pola_zo_strategie_nie_z_ibs():
    """Riziko na obchod sa v každej stratégii volá inak — vie to `SPEC.risk_field`."""
    demo = {"settings": {"strategy": "demo_breakout"}, "params": {"riskDollar": 250.0}}
    assert mc.sizing_of(demo) == 250.0
    # pole IBS v cudzej stratégii nič neznamená
    assert mc.sizing_of({"settings": {"strategy": "demo_breakout"},
                         "params": {"maxLossDollar": 100.0}}) is None
    assert mc.sizing_of({"settings": {"strategy": "neexistuje"}, "params": {"riskDollar": 1}}) is None

# --------------------------------------------------------------------------- #
# CLI nad históriou behov
# --------------------------------------------------------------------------- #


def _run(store_root, run_id: str, fee: float = 0.0005, trades=SAMPLE, status: str = "done"):
    from tester.webapp.store import RunStore

    store = RunStore(store_root)
    store.save(
        {"id": run_id, "status": status, "note": "test",
         "settings": {"pair": "BTC/USDT:USDT", "timeframe": "3m", "fee": fee},
         "result": {"trades": len(trades), "stake_currency": "USDT"}},
        trades=trades,
    )
    return store


def test_cli_vezme_poplatok_z_behu(tmp_path, monkeypatch, capsys):
    _run(tmp_path, "20260101-120000-aaaaaa", fee=0.0005)
    monkeypatch.setattr(mc, "MIN_TRADES", 1)
    monkeypatch.setattr("tester.webapp.store.RUNS_DIR", tmp_path)
    assert mc.main(["20260101-120000-aaaaaa", "--iterations", "200", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["fee_pct"] == pytest.approx(0.05)      # 0,0005 zlomku = 0,05 %
    assert out["run_id"] == "20260101-120000-aaaaaa"
    assert out["n"] == len(SAMPLE)


def test_cli_bez_argumentu_vezme_posledny_beh_s_obchodmi(tmp_path, monkeypatch, capsys):
    _run(tmp_path, "20260101-120000-aaaaaa")
    _run(tmp_path, "20260102-120000-bbbbbb", trades=[], status="failed")
    monkeypatch.setattr("tester.webapp.store.RUNS_DIR", tmp_path)
    assert mc.main(["--iterations", "200", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["run_id"] == "20260101-120000-aaaaaa"


def test_cli_hlasi_neznamy_beh(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("tester.webapp.store.RUNS_DIR", tmp_path)
    assert mc.main(["20260101-120000-cccccc"]) == 1
    assert "v histórii nie je" in capsys.readouterr().out
