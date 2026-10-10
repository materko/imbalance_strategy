"""SWEEP FVG 1.0: engine na syntetických 5m baroch MNQ.

Testuje sa mechanika, nie edge: výber likvidity → CHoCH → FVG → limitka na okraji FVG, SL za extrém výberu.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType, SizeSpec
from tradebot.strategies.sweepfvg import BreakType, EntryModel, SweepFvgConfig, SweepFvgEngine

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
OKNO = MarketContext(in_trade_window=True)
T0 = int(datetime(2025, 9, 2, 10, 0, tzinfo=NY).timestamp() * 1000)

#: BSL 110 (swing bar 2), swing low 104.5 (bar 4), výber 112 (bar 6), CHoCH zavretím 104 (bar 8),
#: medvedí FVG 109–108 (low baru 6 nad high baru 8)
BARS = [(100, 102, 98, 101), (101, 105, 100, 104), (104, 110, 103, 109), (109, 109, 105, 106),
        (106, 106.5, 104.5, 105), (105, 108, 105, 107), (109, 112, 109, 111), (111, 111.5, 107, 107.5),
        (107.5, 108, 103.5, 104)]


def cfg(**kw) -> SweepFvgConfig:
    base = dict(liqUse5m=True, liqUse15m=False, liqUse60m=False, liqPivotLen=1, liqMinDispAtr=SizeSpec(0.0, "atr"),
                structPivotLen=1, atrLen=2, fvgMinAtr=SizeSpec(0.0, "atr"), slBufferAtr=SizeSpec(0.0, "atr"))
    base.update(kw)
    return SweepFvgConfig(**base)


def run(c: SweepFvgConfig):
    e = SweepFvgEngine(c, MNQ, 5)
    return e, [e.on_bar(Bar(T0 + i * 300_000, *ohlc, 100.0), None, OKNO) for i, ohlc in enumerate(BARS)]


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_vyber_choch_a_limitka_na_okraji_fvg():
    e, outs = run(cfg())
    assert not any(entries(o) for o in outs[:-1])                     # pred zlomom nič
    en = entries(outs[-1])
    assert len(en) == 1 and en[0].order_type is OrderType.LIMIT
    p = en[0].plan
    assert p.direction is Direction.SHORT and p.entry == 108.0 and p.stop_loss == 112.0
    assert p.take_profit == 100.0                                    # RR 2 zo stopu 4
    assert e.setup is not None and e.setup.kind == "CHoCH"
    kinds = {d.kind.value for d in outs[-1].drawings if hasattr(d, "kind")}
    assert {"sf_struct", "sf_fvg"} <= kinds


def test_vstup_na_strede_a_ciel_v_bodoch():
    _, outs = run(cfg(entryLevel=EntryModel.MID, tpMode="points", tpPoints=SizeSpec(6.0, "abs")))
    p = entries(outs[-1])[0].plan
    assert p.entry == 108.5 and p.take_profit == 102.5


def test_len_bos_choch_neobchoduje():
    _, outs = run(cfg(breakType=BreakType.BOS))
    assert not any(entries(o) for o in outs)


def test_bez_vyberu_likvidity_nic():
    c = cfg()
    e = SweepFvgEngine(c, MNQ, 5)
    bars = list(BARS)
    bars[6] = (109, 109.5, 109, 109.2)                                # vrchol 110 nezobratý
    outs = [e.on_bar(Bar(T0 + i * 300_000, *ohlc, 100.0), None, OKNO) for i, ohlc in enumerate(bars)]
    assert not any(entries(o) for o in outs)


def test_predhistoria_da_rovnaky_stav():
    a = SweepFvgEngine(cfg(), MNQ, 5)
    b = SweepFvgEngine(cfg(), MNQ, 5)
    bars = [Bar(T0 + i * 300_000, *ohlc, 100.0) for i, ohlc in enumerate(BARS)]
    for x in bars:
        a.on_bar(x, None, OKNO)
    b._seed(bars, None)
    assert [(lv.side, lv.price) for lv in a.levels] == [(lv.side, lv.price) for lv in b.levels]
    assert (a.setup.extreme, a.setup.fvg.top) == (b.setup.extreme, b.setup.fvg.top)
