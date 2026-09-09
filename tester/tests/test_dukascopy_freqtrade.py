"""Dukascopy symbol cez Freqtrade — market info z inštrumentu.

Pre pár, ktorý nosná burza nepozná, nemá Freqtrade market info (presnosť ceny, krok
množstva, limity) a padol by na „Can't get market information for symbol …" až pri prvom
obchode. Dodáva ho `TradebotStrategyBase.bot_start` z `InstrumentSpec`.

Chýbajúce timeframy rieši `tester.timeframes` a `ensure_timeframe` v adaptéri — testy
sú v `tester/tests/test_timeframes.py` a `tradebot/tests/test_freqtrade_timeframes.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from tradebot.core.types import INSTRUMENTS

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
