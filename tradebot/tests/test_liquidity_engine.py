"""Liquidity: engine na syntetických baroch.

Testuje sa mechanika: či z výrazného swing vrcholu vznikne buy-side likvidita až po potvrdení,
či sa rovnaké vrcholy zlúčia, a či vybratie likvidity so zavretím späť dá sweep a so zavretím
za ňou prerazenie — a že úroveň sa po vybratí prestane sledovať a nakreslí sa po miesto vybratia.
"""

from __future__ import annotations

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction
from tradebot.strategies.liquidity import LiquidityConfig, LiquidityEngine

T0 = 1_756_821_600_000          # utorok 2025-09-02 14:00 UTC
MIN5 = 300_000
OKNO = MarketContext(in_trade_window=True)
MNQ = INSTRUMENTS["mnq_databento"]


def _cfg(**kw) -> LiquidityConfig:
    base = dict(liqUse5m=True, liqUse15m=False, liqUse60m=False, liqPivotLen=2, liqMinDispAtr=0.0,
                atrLen=3, breakBufferAtr=0.0, entryModel="close", cooldownBars=0, setupMaxBars=5,
                liqEqualTolAtr=0.05, entryMaxDistAtr=10.0)
    base.update(kw)
    return LiquidityConfig(**base)


def _bar(i: int, h: float, lo: float, c: float, o: float | None = None) -> Bar:
    return Bar(time=T0 + i * MIN5, open=o if o is not None else (h + lo) / 2, high=h, low=lo, close=c, volume=10.0)


#: vrchol 110 na indexe 3, potom pokles — swing s dvoma barmi z každej strany
_BARS = [(101, 99, 100), (103, 100, 102), (106, 102, 105), (110, 104, 107), (106, 101, 102),
         (103, 98, 99), (101, 97, 98), (100, 96, 97), (99, 95, 96)]


def _run(engine, rows, start=0):
    outs = []
    for i, (h, lo, c) in enumerate(rows):
        outs.append(engine.on_bar(_bar(start + i, h, lo, c), None, OKNO))
    return outs


def test_z_vyrazneho_vrcholu_vznikne_buy_side_likvidita():
    engine = LiquidityEngine(_cfg(), MNQ, 5)
    _run(engine, _BARS)
    buy = [lv for lv in engine.levels if lv.side == "buy"]
    assert [lv.price for lv in buy] == [110]
    assert buy[0].start_ms == T0 + 3 * MIN5, "úroveň sa kreslí od swing baru"


def test_prerazenie_likvidity_dá_long_a_úroveň_sa_nakreslí_po_vybratie():
    engine = LiquidityEngine(_cfg(tradeMode="breakout"), MNQ, 5)
    _run(engine, _BARS)
    n = len(_BARS)
    outs = _run(engine, [(104, 97, 103), (112, 103, 111.5)], start=n)
    assert not [lv for lv in engine.levels if lv.side == "buy"], "vybratá likvidita sa už nesleduje"
    lines = [d for d in outs[-1].drawings if getattr(d, "kind", None) and d.kind.name == "LIQ_BUY"]
    assert lines and lines[0].y1 == lines[0].y2 == 110
    entries = [o for o in outs[-1].orders if o.action is OrderAction.ENTRY]
    assert entries and entries[0].direction is Direction.LONG


def test_sweep_likvidity_dá_short():
    engine = LiquidityEngine(_cfg(tradeMode="sweep"), MNQ, 5)
    _run(engine, _BARS)
    n = len(_BARS)
    # knôt nad 110 a medvedie zavretie späť pod ňu — sweep aj vstupný signál na tej istej sviečke
    outs = _run(engine, [(104, 97, 103), (111, 103, 104)], start=n)
    entries = [o for o in outs[-1].orders if o.action is OrderAction.ENTRY]
    assert entries and entries[0].direction is Direction.SHORT
    assert entries[0].plan.stop_loss > 111, "stop za knôtom sweepu"


def test_signal_daleko_od_likvidity_nevstupi():
    """Sweep áno, ale medvedia sviečka príde až keď je cena ďaleko pod úrovňou — žiadny vstup."""
    engine = LiquidityEngine(_cfg(tradeMode="sweep", entryMaxDistAtr=0.5, entryModel="close"), MNQ, 5)
    _run(engine, _BARS)
    n = len(_BARS)
    outs = _run(engine, [(104, 97, 103), (111, 103, 108, ), (108, 100, 100.5)], start=n)
    assert not [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]


def test_rovnake_vrcholy_sa_zlucia():
    engine = LiquidityEngine(_cfg(liqEqualTolAtr=0.5), MNQ, 5)
    rows = _BARS + [(104, 97, 103), (107, 102, 106), (109.98, 105, 106), (106, 100, 101), (103, 98, 99), (102, 97, 98)]
    _run(engine, rows)
    buy = [lv for lv in engine.levels if lv.side == "buy"]
    assert len(buy) == 1 and buy[0].strength == 2 and buy[0].price == 110
