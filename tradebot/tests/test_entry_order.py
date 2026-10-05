"""Spoločný typ vstupu market / limit (`tradebot.core.entry_order`) na jednoduchom engine."""

from __future__ import annotations

from dataclasses import dataclass

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.engine import EngineOutput
from tradebot.core.entry_order import EntryOrderEngine, EntryOrderType, wrap_entry_order
from tradebot.core.orders import OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import INSTRUMENTS, Direction, OrderType

MNQ = INSTRUMENTS["mnq_databento"]


@dataclass
class _Cfg:
    entryOrderType: EntryOrderType = EntryOrderType.LIMIT
    limitOffsetPct: int = 50
    limitValidBars: int = 2
    limitKeepRR: bool = True


class _Eng:
    """Na každom bare pošle market long: vstup 110, stop 100, cieľ 130 (RR 2)."""
    inst = MNQ

    def on_bar(self, bar, htf=None, ctx=None):
        out = EngineOutput()
        plan = TradePlan(direction=Direction.LONG, entry=110.0, stop_loss=100.0, take_profit=130.0, qty=10.0, sl_distance=10.0)
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"e{bar.time}", 0, direction=Direction.LONG, plan=plan,
                                      order_type=OrderType.MARKET))
        return out


def _bar(t):
    return Bar(time=t, open=104, high=112, low=104, close=110, volume=1)


def test_market_nechá_engine_bez_obalu():
    e = _Eng()
    assert wrap_entry_order(e, _Cfg(entryOrderType=EntryOrderType.MARKET)) is e


def test_limitka_na_strede_sviecky_so_zachovanym_rr_a_rovnakym_rizikom():
    w = EntryOrderEngine(_Eng(), _Cfg())
    o = w.on_bar(_bar(0), None, MarketContext(in_trade_window=True)).orders[0]
    assert o.order_type is OrderType.LIMIT
    assert o.plan.entry == 106 and o.plan.stop_loss == 100 and o.plan.take_profit == 118   # RR 2 zo 106
    assert abs(o.plan.qty - 10 * 10 / 6) < 1e-9


def test_kym_limitka_caka_dalsie_vstupy_sa_zahodia_a_po_platnosti_sa_zrusi():
    w = EntryOrderEngine(_Eng(), _Cfg())
    ctx = MarketContext(in_trade_window=True)
    first = w.on_bar(_bar(0), None, ctx).orders
    assert len(first) == 1
    assert w.on_bar(_bar(1), None, ctx).orders == []
    cancel = w.on_bar(_bar(2), None, ctx).orders
    assert cancel[0].action is OrderAction.CANCEL and cancel[0].order_id == first[0].order_id
    assert cancel[1].action is OrderAction.ENTRY, "po zrušení môže prísť nový vstup"
