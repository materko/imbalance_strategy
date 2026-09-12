"""Hyperopt s nula obchodmi v každej epoche musí povedať prečo, nie ukázať tabuľku núl."""

from __future__ import annotations

from tester import hyperopt as ho


def epochy(*obchody):
    return [{"epoch": i, "trades": t, "loss": 100000.0, "params": {}} for i, t in enumerate(obchody)]


NAST = {"pair": "NAS100/USD", "timeframe": "3m", "wallet": 10000, "profile": "nas100.json"}


def test_ked_aspon_jedna_epocha_obchoduje_nic_sa_nehlasi():
    assert ho.zero_trades_note(epochy(0, 0, 12), "", NAST) == ""


def test_bez_epoch_nic_sa_nehlasi():
    assert ho.zero_trades_note([], "", NAST) == ""


def test_signaly_boli_ale_obchody_nie_je_odmietnutie_vstupov():
    log = "IBS NAS100/USD: 12445 barov, 147 zon, 31 signalov (31 long / 0 short)"
    veta = ho.zero_trades_note(epochy(0, 0, 0), log, NAST)

    assert "31 signálov" in veta
    assert "odmietol" in veta
    assert "10000" in veta and "NAS100/USD" in veta     # zadanie je vo vete


def test_ziadny_signal_je_problem_parametrov_alebo_profilu():
    log = "IBS BTC: 1000 barov, 0 zon, 0 signalov (0 long / 0 short)"
    veta = ho.zero_trades_note(epochy(0, 0), log, NAST)

    assert "ani jeden signál" in veta
    assert "profil" in veta


def test_bez_logu_aspon_vysvetli_skore():
    veta = ho.zero_trades_note(epochy(0), "", NAST)

    assert "MAX_LOSS" in veta
