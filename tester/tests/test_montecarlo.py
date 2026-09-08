"""Monte Carlo nad hotovým behom — `tester.montecarlo`."""

from __future__ import annotations

import json

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
    r = mc.analyze([trade(100, 90), trade(100, 110)], iterations=200, seed=0)
    assert r["drawdown"]["observed"] == pytest.approx(10.0)


def test_permutacia_nemeni_sucet_ale_meni_cestu():
    r = mc.analyze(SAMPLE * 4, iterations=2000, seed=0)
    dd = r["drawdown"]
    assert dd["worst"] > dd["observed"]      # existuje horšie poradie tých istých obchodov
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
