"""Trendline Breakout: engine na syntetických baroch.

Testuje sa mechanika, nie edge: či sa z dvoch klesajúcich vrcholov nakreslí odpor, či sa
jeho prerazenie zatvorením obchoduje raz a so stopom za čiarou, a či čiara prerazená
sviečkou medzi kotvami neplatí.
"""

from __future__ import annotations

import pytest

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.trendlines import EntryMode, TrendlineConfig, TrendlineEngine

#: utorok 2025-09-02 14:00 UTC — pracovný deň, `weekdaysOnly` nič neodfiltruje
T0 = 1_756_821_600_000
MIN5 = 300_000
OKNO = MarketContext(in_trade_window=True)
MNQ = INSTRUMENTS["mnq_databento"]


def _cfg(**kw) -> TrendlineConfig:
    base = dict(lineTF="5", pivotLen=2, minAnchorGap=3, atrLen=3, touchTolAtr=0.05,
                breakBufferAtr=0.0, minClosePosPct=0, cooldownBars=0, riskDollar=100.0)
    base.update(kw)
    return TrendlineConfig(**base)


def _bars(highs: list[float]) -> list[Bar]:
    """Bary s daným high; telo 1 bod pod ním, rozsah 2 body."""
    return [Bar(time=T0 + i * MIN5, open=h - 1.5, high=h, low=h - 2.0, close=h - 1.0, volume=10.0)
            for i, h in enumerate(highs)]


#: dva klesajúce vrcholy (index 5: 110, index 11: 107) v inak nízkom teréne
_PEAKS = [100, 101, 102, 104, 106, 110, 106, 104, 103, 104, 105, 107, 105, 103, 102, 102, 101, 101, 100]


def _run(engine: TrendlineEngine, bars: list[Bar]):
    outs = []
    for b in bars:
        outs.append(engine.on_bar(b, None, OKNO))
    return outs


def test_z_dvoch_klesajucich_vrcholov_vznikne_odpor():
    engine = TrendlineEngine(_cfg(), MNQ, 5)
    _run(engine, _bars(_PEAKS))
    ln = engine.lines.res
    assert ln is not None, "z vrcholov 110 a 107 mal vzniknúť klesajúci odpor"
    assert (ln.y1, ln.y2) == (110, 107)
    assert ln.slope_ms < 0


def test_prerazenie_zatvorenim_da_long_so_stopom_pod_ciarou_a_len_raz():
    engine = TrendlineEngine(_cfg(), MNQ, 5)
    bars = _bars(_PEAKS)
    _run(engine, bars)
    ln = engine.lines.res
    t = bars[-1].time + MIN5
    brk = Bar(time=t, open=100.5, high=108.0, low=100.0, close=107.5, volume=10.0)
    out = engine.on_bar(brk, None, OKNO)
    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    o = entries[0]
    assert o.direction is Direction.LONG and o.order_type is OrderType.MARKET
    line_now = ln.value(t + MIN5)
    assert o.plan.stop_loss < line_now < o.plan.entry
    assert o.plan.take_profit == pytest.approx(o.plan.entry + 1.5 * o.plan.sl_distance, abs=0.25)
    # ďalší bar nad čiarou už nový vstup neurobí — čiara je spotrebovaná
    nxt = Bar(time=t + MIN5, open=107.5, high=109.0, low=107.0, close=108.5, volume=10.0)
    assert not [x for x in engine.on_bar(nxt, None, OKNO).orders if x.action is OrderAction.ENTRY]


def test_ciara_prerazena_medzi_kotvami_neplati():
    """Sviečka nad spojnicou vrcholov medzi nimi — to nie je trendovka."""
    highs = list(_PEAKS)
    highs[8] = 112            # medzi kotvami vysoko nad čiarou
    engine = TrendlineEngine(_cfg(maxPivots=2), MNQ, 5)
    _run(engine, _bars(highs))
    ln = engine.lines.res
    assert ln is None or (ln.y1, ln.y2) != (110, 107)


def test_retest_da_limitku_na_ciare():
    engine = TrendlineEngine(_cfg(entryMode="retest"), MNQ, 5)
    bars = _bars(_PEAKS)
    _run(engine, bars)
    t = bars[-1].time + MIN5
    engine.on_bar(Bar(time=t, open=100.5, high=108.0, low=100.0, close=107.5, volume=10.0), None, OKNO)
    assert engine._setup is not None and engine._setup.ordered
    assert engine._pending is not None


def test_tf_trendoviek_musi_byt_nasobkom_grafu():
    with pytest.raises(ValueError):
        TrendlineEngine(_cfg(lineTF="5"), MNQ, 10)
