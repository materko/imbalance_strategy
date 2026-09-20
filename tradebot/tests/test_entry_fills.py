"""Jedno pravidlo vyplnenia čakajúceho vstupu pre všetky zjednodušené fill modely (`entry_fills`)."""

from __future__ import annotations

from tradebot.adapters.freqtrade.runner import EngineRunner, _PendingOrder
from tradebot.core import load_profile
from tradebot.core.orders import OrderAction, OrderIntent, entry_fills
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, OrderType

L, S = Direction.LONG, Direction.SHORT


def test_limit_sa_plni_za_svoju_cenu_alebo_lepsiu():
    assert entry_fills(OrderType.LIMIT, L, 100.0, low=99.0, high=101.0)       # pretnutie
    assert entry_fills(OrderType.LIMIT, L, 100.0, low=100.0, high=101.0)      # dotyk
    assert entry_fills(OrderType.LIMIT, L, 100.0, low=95.0, high=99.0)        # gap cez limitku = lepšia cena
    assert not entry_fills(OrderType.LIMIT, L, 100.0, low=100.25, high=103.0)  # cena ostala nad limitkou
    assert entry_fills(OrderType.LIMIT, S, 100.0, low=101.0, high=104.0)
    assert not entry_fills(OrderType.LIMIT, S, 100.0, low=97.0, high=99.75)


def test_market_sa_plni_vzdy_a_stop_zrkadlovo():
    assert entry_fills(OrderType.MARKET, L, 100.0, low=100.25, high=103.0)
    assert entry_fills(OrderType.MARKET, S, 100.0, low=97.0, high=99.75)
    assert entry_fills(OrderType.STOP, L, 100.0, low=99.0, high=100.0)
    assert not entry_fills(OrderType.STOP, L, 100.0, low=97.0, high=99.75)
    assert entry_fills(OrderType.STOP, S, 100.0, low=100.0, high=101.0)


def test_runner_vyplni_market_vstup_aj_ked_cena_usla():
    """MNQ 2026-09-03 `LONG_944`: market vstup 29177.25, ďalší bar má high 29177.00. Platforma ho
    vyplní na otvorení; model „cena vnútri baru" ho nechal visieť a engine o pozícii nevedel."""
    cfg, inst = load_profile("golden_binance_btcusdt_3m")
    runner = EngineRunner(cfg, inst, 3)
    plan = TradePlan(L, entry=29177.25, stop_loss=29169.25, take_profit=29185.25, qty=1.0, sl_distance=8.0)
    for order_type, expected in ((OrderType.MARKET, True), (OrderType.LIMIT, True)):
        intent = OrderIntent(OrderAction.ENTRY, "LONG_944", 944, direction=L, plan=plan, order_type=order_type)
        runner._orders = {"LONG_944": _PendingOrder(intent)}
        runner._simulate_fills(Bar(0, 29177.0, 29177.0, 29170.0, 29171.0, 1.0))
        assert runner._orders["LONG_944"].filled is expected

    # limitka, ku ktorej sa cena nevrátila, čaká ďalej; market nie
    away = Bar(0, 29180.0, 29190.0, 29178.0, 29185.0, 1.0)
    for order_type, expected in ((OrderType.MARKET, True), (OrderType.LIMIT, False)):
        intent = OrderIntent(OrderAction.ENTRY, "LONG_944", 944, direction=L, plan=plan, order_type=order_type)
        runner._orders = {"LONG_944": _PendingOrder(intent)}
        runner._simulate_fills(away)
        assert runner._orders["LONG_944"].filled is expected
