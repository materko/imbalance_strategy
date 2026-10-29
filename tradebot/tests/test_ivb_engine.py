"""IVB 1.0 (prepis Rust `IvbStrategy`): engine na syntetických 5m baroch v čase New York."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.ivb import IvbConfig, IvbEngine

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]


def ms(day: int, hh: int, mm: int) -> int:
    return int(datetime(2026, 3, day, hh, mm, tzinfo=NY).timestamp() * 1000)


def day_bars(day: int, ib: float, *, breakout: float | None = None, vol: float = 100.0, surge: float = 100.0):
    """Deň 9:00–11:00 po 5 min: IB 9:30–10:00 so šírkou `ib` okolo 100, o 10:00 bar s `breakout` zavretím."""
    out = []
    for k in range(24):
        hh, mm = 9 + k * 5 // 60, k * 5 % 60
        t = ms(day, hh, mm)
        if hh * 100 + mm == 1000 and breakout is not None:
            out.append(Bar(t, 100.0, max(100.0, breakout) + 0.5, min(100.0, breakout) - 0.5, breakout, surge))
        else:
            out.append(Bar(t, 100.0, 100.0 + ib / 2, 100.0 - ib / 2, 100.0, vol))
    return out


def run(engine: IvbEngine, bars, pos: float = 0.0):
    outs = []
    for b in bars:
        outs.append(engine.on_bar(b, None, MarketContext(in_trade_window=True, position_size=pos)))
    return outs


def entries(outs):
    return [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]


def test_stlaceny_ib_a_objem_daju_market_long_so_stopom_a_cielom_v_atr():
    e = IvbEngine(IvbConfig(), MNQ, 5)
    for d in range(2, 7):                                   # päť širokých IB do priemeru
        run(e, day_bars(d, 10.0))
    outs = run(e, day_bars(9, 4.0, breakout=103.0, surge=500.0))
    ent = entries(outs)
    assert len(ent) == 1
    i = ent[0]
    assert i.direction is Direction.LONG and i.order_type is OrderType.MARKET
    p = i.plan
    assert p.entry == 103.0 and p.stop_loss < 103.0 < p.take_profit
    # stop 3 ATR a cieľ 2 ATR od zavretia (ATR baru signálu), zaokrúhlené na tick
    assert (p.entry - p.stop_loss) / (p.take_profit - p.entry) == pytest.approx(1.5, abs=0.05)


def test_siroky_ib_ani_slaby_objem_nevstupia():
    e = IvbEngine(IvbConfig(), MNQ, 5)
    for d in range(2, 7):
        run(e, day_bars(d, 4.0))
    assert not entries(run(e, day_bars(9, 8.0, breakout=106.0, surge=500.0)))   # IB 2× priemer
    e = IvbEngine(IvbConfig(), MNQ, 5)
    for d in range(2, 7):
        run(e, day_bars(d, 10.0))
    assert not entries(run(e, day_bars(9, 4.0, breakout=103.0, surge=100.0)))  # objem bez nárastu


def test_pokus_bez_prierazu_sa_rata_ako_v_predlohe():
    """Predloha zvýši počítadlo pri splnenom IB a objeme aj bez prierazu — dva také bary vyčerpajú deň."""
    e = IvbEngine(IvbConfig(), MNQ, 5)
    for d in range(2, 7):
        run(e, day_bars(d, 10.0))
    bars = day_bars(9, 4.0)
    bars = [Bar(b.time, b.open, b.high, b.low, b.close, 500.0) if b.time in (ms(9, 10, 0), ms(9, 10, 5)) else b
            for b in bars]
    bars = [Bar(b.time, 100.0, 104.0, 100.0, 103.5, 500.0) if b.time == ms(9, 10, 10) else b for b in bars]
    assert not entries(run(e, bars))
    assert e.todays_trades == 2


def test_smer_len_short_ignoruje_long_prieraz():
    e = IvbEngine(IvbConfig(direction=2), MNQ, 5)
    for d in range(2, 7):
        run(e, day_bars(d, 10.0))
    assert not entries(run(e, day_bars(9, 4.0, breakout=103.0, surge=500.0)))


def test_koniec_dna_zavrie_poziciu():
    e = IvbEngine(IvbConfig(flattenEod=True, eodFlatten=1030), MNQ, 5)
    run(e, day_bars(2, 10.0))
    out = e.on_bar(Bar(ms(3, 10, 30), 100, 101, 99, 100, 100), None, MarketContext(in_trade_window=True, position_size=1.0))
    assert out.close_session
