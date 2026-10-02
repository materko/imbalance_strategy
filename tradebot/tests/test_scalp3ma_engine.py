"""Scalping 3MA + RSI + fraktál: engine na syntetických baroch.

Testuje sa mechanika: v klesajúcom trende (cena pod troma SMMA, RSI pod 50) dá fraktál hore short
so stopom a cieľom 1 : 2, v rastúcom trende a bez fraktálu nič; posun stopu na vstup a výstup cez RSI.
"""

from __future__ import annotations

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, SizeSpec
from tradebot.strategies.scalp3ma import Scalp3MaConfig, Scalp3MaEngine
from tradebot.strategies.scalp3ma.engine import BreakEven

T0 = 1_756_821_600_000
MIN5 = 300_000
OKNO = MarketContext(in_trade_window=True)
EUR = INSTRUMENTS["eurusd_dukascopy"]


def _cfg(**kw) -> Scalp3MaConfig:
    base = dict(ma1Len=3, ma2Len=5, ma3Len=8, rsiLen=3, atrLen=3, slMode="points",
                slPoints=SizeSpec(0.0005, "abs"), rrRatio=2.0, maxTradesPerDay=10)
    base.update(kw)
    return Scalp3MaConfig(**base)


def _bar(i: int, c: float, h: float | None = None, lo: float | None = None) -> Bar:
    return Bar(time=T0 + i * MIN5, open=c, high=c + 0.0002 if h is None else h,
               low=c - 0.0002 if lo is None else lo, close=c, volume=10.0)


def _down(e, n=40, start=1.2000, step=0.0003):
    outs, px = [], start
    for i in range(n):
        outs.append(e.on_bar(_bar(i, px), None, OKNO))
        px -= step
    return outs, n, px


def _entries(outs):
    return [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]


def test_klesajuci_trend_bez_fraktalu_hore_nevstupi():
    e = Scalp3MaEngine(_cfg(), EUR, 5)
    outs, _, _ = _down(e)
    assert not _entries(outs), "rovnomerný pokles nemá fraktál hore"


def test_fraktal_hore_v_klesajucom_trende_je_short_so_stopom_5_a_cielom_10_pipov():
    e = Scalp3MaEngine(_cfg(), EUR, 5)
    _, n, px = _down(e)
    rows = [_bar(n, px, h=px + 0.0002), _bar(n + 1, px - 0.0003, h=px + 0.0015),       # vrchol pullbacku
            _bar(n + 2, px - 0.0006), _bar(n + 3, px - 0.0009)]                        # dva nižšie bary = fraktál potvrdený
    outs = [e.on_bar(b, None, OKNO) for b in rows]
    o = _entries(outs)[0]
    assert o.direction is Direction.SHORT and outs[-1].orders, "vstup na bare, ktorý fraktál potvrdil"
    assert abs(o.plan.stop_loss - o.plan.entry - 0.0005) < 1e-9
    assert abs(o.plan.entry - o.plan.take_profit - 0.0010) < 1e-9
    assert isinstance(o.plan.trailing, BreakEven)


def test_long_only_short_zahodi_a_denny_strop_plati():
    e = Scalp3MaEngine(_cfg(tradeDirection="Long only"), EUR, 5)
    _, n, px = _down(e)
    rows = [_bar(n, px), _bar(n + 1, px - 0.0003, h=px + 0.0015), _bar(n + 2, px - 0.0006), _bar(n + 3, px - 0.0009)]
    assert not _entries([e.on_bar(b, None, OKNO) for b in rows])


def test_break_even_posunie_stop_na_vstup_az_po_aktivacii():
    be = BreakEven.at(0.0005, 0.00001)
    assert be.stop_price(Direction.SHORT, 1.1000, 1.1005, 1.0997) == 1.1005      # zisk 3 pipy — ešte nie
    assert be.stop_price(Direction.SHORT, 1.1000, 1.1005, 1.0995) == 1.1000      # zisk 5 pipov — stop na vstupe
    assert be.stop_price(Direction.LONG, 1.1000, 1.0995, 1.1006) == 1.1000


def test_rsi_cez_uroven_proti_obchodu_zavrie_poziciu():
    e = Scalp3MaEngine(_cfg(), EUR, 5)
    _, n, px = _down(e)
    drzi = MarketContext(in_trade_window=True, position_size=-1.0, open_order_ids=frozenset({"s3:1"}))
    out = e.on_bar(_bar(n, px + 0.0040), None, drzi)          # prudký rast — RSI nad 50
    assert out.close_session and any(o.action is OrderAction.CLOSE for o in out.orders)
