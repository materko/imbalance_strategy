"""MTK EMAS: priemery a engine na syntetických baroch (MNQ, 4h)."""

from __future__ import annotations

import pandas as pd
import pytest

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.config import ConfigError
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.mtkemas import MtkEmasConfig, MtkEmasEngine
from tradebot.strategies.mtkemas.ma import Atr, make_ma

MNQ = INSTRUMENTS["mnq_databento"]
STEP = 240 * 60_000
OKNO = MarketContext(in_trade_window=True)


def _bars(closes, rng=10.0):
    return [Bar(time=1_700_000_000_000 + i * STEP, open=c, high=c + rng / 2, low=c - rng / 2, close=c, volume=100.0 + i)
            for i, c in enumerate(closes)]


@pytest.mark.parametrize("kind", ["ema", "sma", "wma", "rma", "vwma"])
def test_priemery_ako_pandas(kind):
    import numpy as np
    xs = [100 + 5 * np.sin(i / 3) + i * 0.1 for i in range(80)]
    vs = [100.0 + i for i in range(80)]
    s = pd.Series(xs)
    want = {"ema": s.ewm(span=10, adjust=False, min_periods=10).mean(), "sma": s.rolling(10).mean(),
            "rma": s.ewm(alpha=0.1, adjust=False, min_periods=10).mean(),
            "wma": s.rolling(10).apply(lambda a: np.dot(a, np.arange(1, 11)) / 55, raw=True),
            "vwma": (s * pd.Series(vs)).rolling(10).sum() / pd.Series(vs).rolling(10).sum()}[kind]
    ma = make_ma(kind, 10)
    got = [ma.push(x, v) for x, v in zip(xs, vs)]
    for g, w in zip(got, want):
        assert (g is None) == pd.isna(w)
        if g is not None:
            assert g == pytest.approx(w, rel=1e-9)


def test_dema_tema_hma_kama_startuju_po_dost_baroch():
    for kind, n, first in (("dema", 5, 10), ("tema", 5, 15), ("hma", 9, 9 + 3 - 1 - 1), ("kama", 10, 10)):
        ma = make_ma(kind, n)
        out = [ma.push(100.0 + i, 1.0) for i in range(40)]
        assert out.index(next(x for x in out if x is not None)) == first, kind


def test_atr_rma_true_range():
    a = Atr(14)
    assert a.push(110, 100, 105) == 10.0
    assert a.push(120, 104, 118) == pytest.approx(10.0 * 13 / 14 + 16.0 / 14)


def test_cena_prekrizi_priemer_long_stop_atr_trailing_a_zamok():
    cfg = MtkEmasConfig(maType="sma", signalMode="price", slowLen=5, slAtr=1.5, trailAtr=4.0, beAtR=1.0)
    e = MtkEmasEngine(cfg, MNQ, 240)
    outs = [e.on_bar(b, ctx=OKNO) for b in _bars([100] * 6 + [90, 85, 80, 120])]
    entries = [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    o = entries[0]
    assert o.direction is Direction.LONG and o.order_type is OrderType.MARKET and o.plan.entry == 120
    atr = e.atr.value
    assert o.plan.sl_distance == pytest.approx(1.5 * atr)
    tr = o.plan.trailing
    assert tr.offset_price_distance == pytest.approx(4 * atr) and tr.activation_price_distance == 0
    assert tr.lock_activation_distance == pytest.approx(1.5 * atr) and tr.lock_level_distance == 0
    # zámok: pri zisku 1 R stop na vstup, trailing ešte nižšie
    assert tr.stop_price(Direction.LONG, 120, 100, 120 + 1.5 * atr) == 120


def test_len_longy_a_opacne_krizenie_zavrie():
    cfg = MtkEmasConfig(maType="sma", signalMode="price", slowLen=5)
    e = MtkEmasEngine(cfg, MNQ, 240)
    bars = _bars([100] * 6 + [90, 120, 125, 130, 80])
    outs = [e.on_bar(b, ctx=OKNO) for b in bars[:-1]]
    (entry,) = [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]
    v = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({entry.order_id}))
    out = e.on_bar(bars[-1], ctx=v)
    (c,) = [o for o in out.orders if o.action is OrderAction.CLOSE]
    assert c.reason == "opačné kríženie" and not [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_cross_rychly_musi_byt_kratsi():
    with pytest.raises(ConfigError, match="fastLen"):
        MtkEmasConfig(signalMode="cross", fastLen=30, slowLen=20)
