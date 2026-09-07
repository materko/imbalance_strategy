"""Dukascopy symbol cez Freqtrade — sviečky po timeframoch a market info z inštrumentu.

Freqtrade si vyšší TF z 1m nedopočíta a pre pár, ktorý nosná burza nepozná, nemá
market info. Oboje dodáva port: `dukas_import --target freqtrade` vyrobí súbory,
`TradebotStrategyBase.bot_start` doplní market z `InstrumentSpec`. Keby sa čokoľvek
z toho stratilo, backtest padne až pri prvom obchode — preto sú tu testy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from tradebot.core.types import INSTRUMENTS
from tradebot.core.candles import resample_ohlcv
from tester.dukas_import import write_freqtrade

INST = INSTRUMENTS["nas100_dukascopy"]
MIN = 60_000
T0 = 1_736_121_600_000  # 2025-01-06 00:00 UTC


def m1(n: int) -> "pd.DataFrame":
    return pd.DataFrame({
        "date": [pd.Timestamp(T0 + i * MIN, unit="ms", tz="UTC") for i in range(n)],
        "open": [100.0 + i for i in range(n)], "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)], "close": [100.5 + i for i in range(n)],
        "volume": [1.0] * n,
    })


# --------------------------------------------------------------------------- #
# sviečky pre Freqtrade
# --------------------------------------------------------------------------- #


def test_write_freqtrade_vyrobi_subor_na_kazdy_timeframe(tmp_path: Path):
    files = write_freqtrade(m1(60), "NAS100_USD", datadir=tmp_path, verbose=False)

    assert [f.name for f in files] == [
        "NAS100_USD-1m.feather", "NAS100_USD-3m.feather", "NAS100_USD-5m.feather"]
    assert len(pd.read_feather(files[0])) == 60
    assert len(pd.read_feather(files[1])) == 20
    assert len(pd.read_feather(files[2])) == 12


def test_svicky_pre_freqtrade_su_tie_iste_ako_v_emulatore(tmp_path: Path):
    """Inak by Freqtrade beh a emulátor MultiCharts počítali z iných barov."""
    base = m1(60)
    files = write_freqtrade(base, "NAS100_USD", datadir=tmp_path, timeframes=["3m"], verbose=False)

    assert pd.read_feather(files[0]).equals(resample_ohlcv(base, 3))


def test_agregacia_zarovna_na_nasobky_tf_od_epochy():
    """Ako TradingView aj MultiCharts: 3m bar začína na 00, 03, 06… nie od prvého baru."""
    df = m1(10).iloc[1:]  # séria začína o 00:01
    out = resample_ohlcv(df, 3)

    assert [str(t)[11:16] for t in out["date"]] == ["00:00", "00:03", "00:06", "00:09"]
    assert out.iloc[0]["open"] == 101.0 and out.iloc[0]["high"] == 103.0  # z barov 1 a 2


# --------------------------------------------------------------------------- #
# market info pre pár, ktorý na burze nie je
# --------------------------------------------------------------------------- #


class _Exchange:
    """Toľko z Freqtrade burzy, koľko `bot_start` potrebuje."""

    def __init__(self, precision_mode: int = 4, markets: dict | None = None):
        self.precisionMode = precision_mode
        self._markets = {} if markets is None else markets


class _DP:
    def __init__(self, exchange):
        self._exchange = exchange


def _strategy(exchange, pair: str = "NAS100/USD", instrument=INST):
    """Stratégia bez volania `__init__` — testujeme len `bot_start`."""
    from tradebot.adapters.freqtrade.base import TradebotStrategyBase

    s = TradebotStrategyBase.__new__(TradebotStrategyBase)
    s.tb_inst = instrument
    s.dp = _DP(exchange)
    s.config = {"exchange": {"name": "bitstamp", "pair_whitelist": [pair]}}
    return s


def test_market_sa_doplni_z_instrumentu_ked_ho_burza_nepozna():
    ex = _Exchange()
    _strategy(ex).bot_start()

    m = ex._markets["NAS100/USD"]
    assert m["symbol"] == "NAS100/USD" and m["base"] == "NAS100" and m["quote"] == "USD"
    assert m["spot"] is True and m["contract"] is False and m["active"] is True
    # precisionMode 4 = TICK_SIZE: presnosť je krok, nie počet desatinných miest
    assert m["precision"] == {"price": INST.tick_size, "amount": INST.qty_step}
    assert m["limits"]["amount"]["min"] == INST.min_qty
    assert m["limits"]["leverage"]["max"] == 1.0


def test_precisia_ako_pocet_desatinnych_miest_pri_inom_rezime():
    ex = _Exchange(precision_mode=2)  # ccxt DECIMAL_PLACES
    _strategy(ex).bot_start()

    assert ex._markets["NAS100/USD"]["precision"] == {"price": 2, "amount": 0}


def test_skutocny_trh_sa_neprepise():
    real = {"symbol": "NAS100/USD", "precision": {"price": 0.5, "amount": 1.0}}
    ex = _Exchange(markets={"NAS100/USD": real})
    _strategy(ex).bot_start()

    assert ex._markets["NAS100/USD"] is real


def test_burzovy_instrument_sa_nedoplna():
    """Doplnenie sa robí len pre inštrument mimo burzy — inak by sme prepisovali realitu."""
    ex = _Exchange()
    _strategy(ex, pair="BTC/USDT:USDT", instrument=INSTRUMENTS["btcusdt_binance"]).bot_start()

    assert ex._markets == {}
