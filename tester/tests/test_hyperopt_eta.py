"""Odhad, ako dlho ešte hyperopt pobeží."""

from __future__ import annotations

from tester import hyperopt as ho


def test_pocita_epochy_ako_riadky(tmp_path):
    f = tmp_path / "x.fthypt"
    f.write_text('{"a":1}\n{"a":2}\n\n{"a":3}\n', encoding="utf-8")

    assert ho.count_epochs(f) == 3
    assert ho.count_epochs(tmp_path / "neni.fthypt") == 0
    assert ho.count_epochs(None) == 0


def test_pred_prvou_epochou_odhad_nie_je():
    """Freqtrade najprv načítava dáta — tempo z toho by odhad nafúklo."""
    p = ho.eta(0, 200, started=0.0, first_done_at=None, first_done=0, now=90.0)

    assert p["done"] == 0 and p["eta_s"] is None
    assert p["elapsed_s"] == 90


def test_z_jednej_davky_odhad_nie_je():
    p = ho.eta(8, 200, started=0.0, first_done_at=60.0, first_done=8, now=65.0)

    assert p["eta_s"] is None


def test_tempo_sa_meria_od_prvej_hotovej_epochy_nie_od_startu():
    """Štart o 0, prvých 10 epoch hotových v 100 s (z toho väčšina príprava), ďalších
    10 epoch za 50 s → 5 s na epochu, zostáva 180 epoch = 900 s. Od štartu by vyšlo
    7,5 s na epochu a odhad 1350 s."""
    p = ho.eta(20, 200, started=0.0, first_done_at=100.0, first_done=10, now=150.0)

    assert p["s_per_epoch"] == 5.0
    assert p["eta_s"] == 900


def test_hotovy_hyperopt_ma_nulovy_zvysok():
    p = ho.eta(200, 200, started=0.0, first_done_at=10.0, first_done=8, now=500.0)

    assert p["eta_s"] == 0


def test_pocas_cakania_na_davku_odhad_klesa_nie_rastie():
    """Epochy chodia po dávkach. Prvá dávka (4) v 100 s, druhá (8) v 140 s → 10 s na
    epochu. Keď potom 30 s nič nepríde, odhad musí klesnúť o tých 30 s, nie narásť."""
    hned = ho.eta(8, 24, 0.0, 100.0, 4, now=140.0, last_done_at=140.0)
    neskor = ho.eta(8, 24, 0.0, 100.0, 4, now=170.0, last_done_at=140.0)

    assert hned["eta_s"] == 160
    assert neskor["eta_s"] == 130


def test_iny_bezaci_hyperopt_sa_rozpozna():
    """Freqtrade vtedy skončí s kódom 0 — bez kontroly by to vyzeralo ako hotový beh."""
    log = ["... INFO - Another running instance of freqtrade Hyperopt detected.",
           "... INFO - Quitting now."]

    assert ho.blocked_by_other(log)
    assert not ho.blocked_by_other(["Starting freqtrade in Hyperopt mode"])
