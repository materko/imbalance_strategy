"""Výstupy Freqtrade adaptéra — TP musí ísť cez ROI, nie cez exit-signál.

Exit-signál sa v backteste vyhodnocuje **aj plní otváracou cenou sviečky**, takže
knôt cez TP neurobí nič a keď sa napokon spustí, cena je už za TP. Na golden dátach
to výstupy posúvalo o jednu až tri sviečky neskôr a o 7-11 bodov vyššie než TradingView.
ROI sa naopak vyhodnocuje proti `high` sviečky a plní sa presnou cenou.

Testy nekontrolujú freqtrade samotný, len že adaptér používa to správne rozhranie
a odovzdáva doň TP z plánu.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ibs.adapters.freqtrade.runner import SignalRow

strategy_mod = pytest.importorskip("ibs.adapters.freqtrade.strategy")
IBSImbalanceStrategy = strategy_mod.IBSImbalanceStrategy


class _StubTrade:
    """Minimum z freqtrade `Trade`, ktoré `custom_roi` potrebuje."""

    def __init__(self, open_rate: float, is_short: bool = False) -> None:
        self.open_rate = open_rate
        self.is_short = is_short
        self.open_date_utc = datetime(2026, 8, 24, 14, 54, tzinfo=timezone.utc)
        self.asked_for: list[float] = []

    def calc_profit_ratio(self, rate: float) -> float:
        self.asked_for.append(rate)
        return (rate - self.open_rate) / self.open_rate


@pytest.fixture
def strategy(monkeypatch):
    s = IBSImbalanceStrategy.__new__(IBSImbalanceStrategy)
    s._runners = {}
    return s


def _with_signal(strategy, row: SignalRow, ts_ms: int) -> None:
    class _Runner:
        def signal_at_or_before(self, _ts):
            return row

    strategy._runners["BTC/USDT:USDT"] = _Runner()


def test_tp_ide_cez_roi_nie_cez_exit_signal():
    """`custom_exit` na TP by výstup posunul a nadhodnotil — nesmie sa vrátiť."""
    assert IBSImbalanceStrategy.use_custom_roi is True
    assert "custom_exit" not in vars(IBSImbalanceStrategy)


def test_minimal_roi_je_nedosiahnutelne():
    """Globálne ROI nesmie zavrieť obchod skôr než TP z plánu."""
    assert min(IBSImbalanceStrategy.minimal_roi.values()) >= 1.0


def test_custom_roi_odovzda_take_profit_z_planu(strategy):
    trade = _StubTrade(open_rate=79419.5)
    _with_signal(strategy, SignalRow(stop_loss=79231.7, take_profit=79607.3), 0)

    roi = strategy.custom_roi(
        "BTC/USDT:USDT", trade, trade.open_date_utc, 0, "ibs", "long"
    )

    assert trade.asked_for == [79607.3]
    assert roi == pytest.approx((79607.3 - 79419.5) / 79419.5)


def test_custom_roi_bez_signalu_nechá_rozhodnutie_na_freqtrade(strategy):
    trade = _StubTrade(open_rate=79419.5)
    roi = strategy.custom_roi(
        "BTC/USDT:USDT", trade, trade.open_date_utc, 0, "ibs", "long"
    )
    assert roi is None


def test_custom_roi_ignoruje_nan_take_profit(strategy):
    trade = _StubTrade(open_rate=79419.5)
    _with_signal(strategy, SignalRow(stop_loss=79231.7), 0)  # take_profit ostáva NaN
    assert strategy.custom_roi("BTC/USDT:USDT", trade, trade.open_date_utc, 0, "ibs", "long") is None
