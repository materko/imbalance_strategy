"""Výber engine: tá istá stratégia cez Freqtrade aj cez emulátor MultiCharts.

Engine nie je vlastnosť páru — krypto sa dá prehrať emulátorom a Dukascopy CFD cez
Freqtrade. Obmedzuje to len to, aké sviečky sú na disku.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tester import engines
from tradebot.core.types import INSTRUMENTS

BTC = INSTRUMENTS["btcusdt_binance"]
BTC_SPOT = INSTRUMENTS["btcusdt_binance_spot"]
NAS = INSTRUMENTS["nas100_dukascopy"]


@pytest.fixture
def data(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(engines, "DATA", tmp_path / "data")
    return tmp_path


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


# --------------------------------------------------------------------------- #
# kde ktoré dáta ležia
# --------------------------------------------------------------------------- #


def test_cesty_su_pod_zdrojom_a_trhom(data):
    """Adresár je zdroj a trh, nie platforma — dáta sú pre oba enginy jedny."""
    assert engines.freqtrade_file(BTC, "3m") == data / "data/binance/futures/BTC_USDT_USDT-3m-futures.feather"
    assert engines.freqtrade_file(BTC_SPOT, "3m") == data / "data/binance/spot/BTC_USDT-3m.feather"
    assert engines.freqtrade_file(NAS, "3m") == data / "data/dukascopy/futures/NAS100_USD-3m.feather"


def test_datadir_dopocita_freqtradeov_podadresar(data):
    """`futures/` si Freqtrade pridáva sám, pri spote nie — preto rôzny `--datadir`."""
    assert engines.data_dir(BTC) == data / "data/binance"
    assert engines.data_dir(BTC_SPOT) == data / "data/binance/spot"
    assert engines.data_dir(NAS) == data / "data/dukascopy/futures"
    # nech je datadir akykolvek, subor musi vyjst pod market_dir
    for inst in (BTC, BTC_SPOT, NAS):
        assert engines.freqtrade_file(inst, "3m").parent == engines.market_dir(inst)


def test_emulator_cita_ten_isty_strom_ako_freqtrade(data):
    assert engines.one_minute_file(NAS) == data / "data/dukascopy/futures/NAS100_USD-1m.feather"
    assert engines.one_minute_file(BTC) == data / "data/binance/futures/BTC_USDT_USDT-1m-futures.feather"


def test_config_podla_trhu_a_zdroja():
    assert engines.freqtrade_config(BTC).name == "config.binance.json"
    assert engines.freqtrade_config(BTC_SPOT).name == "config.binance.spot.json"
    assert engines.freqtrade_config(NAS).name == "config.dukascopy.json"


# --------------------------------------------------------------------------- #
# dostupnosť podľa dát
# --------------------------------------------------------------------------- #


def test_bez_dat_nie_je_dostupny_ziadny_engine(data):
    assert engines.available(BTC) == []


def test_krypto_sa_da_prehrat_aj_emulatorom(data):
    touch(engines.freqtrade_file(BTC, "3m"))
    touch(engines.one_minute_file(BTC))

    assert engines.available(BTC) == ["freqtrade", "multicharts"]
    assert engines.default_engine(BTC) == "freqtrade"


def test_dukascopy_ma_predvoleny_emulator_aj_ked_su_data_pre_freqtrade(data):
    """Emulátor je pre Dukascopy referencia — sedí s tým, čo v MultiCharts naozaj pobeží."""
    touch(engines.freqtrade_file(NAS, "3m"))
    touch(engines.one_minute_file(NAS))

    assert engines.available(NAS) == ["freqtrade", "multicharts"]
    assert engines.default_engine(NAS) == "multicharts"


def test_dostupnost_je_per_timeframe(data):
    touch(engines.freqtrade_file(BTC, "3m"))

    assert engines.available(BTC, "3m") == ["freqtrade"]
    assert engines.available(BTC, "5m") == []


# --------------------------------------------------------------------------- #
# beh bez obchodov, hoci signály boli
# --------------------------------------------------------------------------- #


def test_signaly_bez_obchodov_daju_upozornenie():
    from tester.webapp.runner import zero_trade_warning

    log = ["IBS NAS100/USD: 12445 barov, 147 zon, 13 signalov (13 long / 0 short)"]
    warning = zero_trade_warning({"trades": 0}, log)

    assert warning and "13 vstupných signálov" in warning and "peňaženku" in warning


def test_bez_signalov_alebo_s_obchodmi_sa_nehlasi_nic():
    from tester.webapp.runner import zero_trade_warning

    log = ["IBS NAS100/USD: 12445 barov, 147 zon, 13 signalov (13 long / 0 short)"]
    assert zero_trade_warning({"trades": 5}, log) is None
    assert zero_trade_warning({"trades": 0}, ["ziadny signal v logu"]) is None
    assert zero_trade_warning({"trades": 0}, ["IBS X: 0 signalov (0 long / 0 short)"]) is None
