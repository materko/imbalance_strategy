"""NB 1.0: engine na syntetických 15m baroch.

Testuje sa mechanika podľa videa: v uptrende (vyšší TF aj SMA grafu) stojí po konsolidácii stop order
nad jej hranou so stopom pod opačnou hranou a cieľom RR; v downtrende zrkadlovo short; mimo okna vstupu
a pri širokom okne order nie je; miesto do cieľa pred swingom vyššieho TF obchod zablokuje; zmena hraníc
order preloží.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.nb import NbConfig, NbEngine

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
M15 = 15 * 60_000
FLAT = MarketContext(in_trade_window=True)
#: krátke SMA a hodinový vyšší TF, aby stačilo pár desiatok barov
FAST = dict(htfTF=60, smaFast=3, smaSlow=5, pivotLen=1, atrLen=5, consBars=8, useRoom=False)


def t0(hour: int = 22, day: int = 2) -> int:
    """2. 9. 2025 (utorok) 22:00 NY."""
    return int(datetime(2025, 9, day, hour, 0, tzinfo=NY).timestamp() * 1000)


def bar(ts: int, c: float, w: float = 1.0) -> Bar:
    return Bar(ts, c, c + w, c - w, c, 100.0)


def run(e: NbEngine, closes, start: int, w: float = 1.0):
    outs = []
    for i, c in enumerate(closes):
        outs.append(e.on_bar(bar(start + i * M15, c, w), None, FLAT))
    return outs


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def trend_then_box(sign: int = 1):
    """48 barov trendu (±2 body na bar), potom 8 barov úzkej konsolidácie, ktorá ide pomaly v smere trendu (šírka pod 2 ATR)."""
    base = 20000.0
    trend = [base + sign * 2 * i for i in range(48)]
    last = trend[-1]
    box = [last + sign * 0.25 * (i + 1) for i in range(8)]
    return trend + box


def test_v_uptrende_stoji_stop_order_nad_konsolidaciou():
    e = NbEngine(NbConfig(**FAST), MNQ, 15)
    closes = trend_then_box(+1)
    outs = run(e, closes, t0())                     # posledný bar sa zavrie 12:00 NY v stredu (okno 2:00–16:00)
    oi = entries(outs[-1])
    assert oi, "po konsolidácii v uptrende má stáť stop order"
    o = oi[0]
    assert o.order_type is OrderType.STOP and o.direction is Direction.LONG
    box = closes[-8:]
    hi, lo = max(box) + 1.0, min(box) - 1.0
    assert o.plan.entry == MNQ.round_price(hi + MNQ.tick_size)
    assert o.plan.stop_loss < lo
    risk = o.plan.entry - o.plan.stop_loss
    assert abs(o.plan.take_profit - (o.plan.entry + 3.0 * risk)) <= MNQ.tick_size


def test_v_downtrende_short_pod_konsolidaciou():
    e = NbEngine(NbConfig(**FAST), MNQ, 15)
    outs = run(e, trend_then_box(-1), t0())
    o = entries(outs[-1])[0]
    assert o.direction is Direction.SHORT and o.order_type is OrderType.STOP
    assert o.plan.stop_loss > o.plan.entry > o.plan.take_profit


def test_mimo_okna_vstupu_order_nie_je():
    e = NbEngine(NbConfig(**FAST, entryStartH=13), MNQ, 15)
    outs = run(e, trend_then_box(+1), t0())
    assert not any(entries(o) for o in outs)


def test_siroke_okno_nie_je_konsolidacia():
    e = NbEngine(NbConfig(**{**FAST, "consMaxWidth": 0.5}), MNQ, 15)
    outs = run(e, trend_then_box(+1), t0())
    assert not entries(outs[-1])


def test_miesto_do_ciela_pred_swingom_vyssieho_tf_zablokuje_long():
    cfg = {**FAST, "useRoom": True, "roomMinR": 2.5}
    e = NbEngine(NbConfig(**cfg), MNQ, 15)
    closes = trend_then_box(+1)
    # swing vyššieho TF tesne nad konsolidáciou (do 2,5 R)
    e.piv_hi.append(max(closes[-8:]) + 3.0)
    outs = run(e, closes, t0())
    assert not entries(outs[-1])


def test_zmena_hranic_prelozi_order():
    e = NbEngine(NbConfig(**FAST), MNQ, 15)
    closes = trend_then_box(+1)
    outs = run(e, closes, t0())
    first = entries(outs[-1])[0]
    out = e.on_bar(bar(t0() + len(closes) * M15, closes[-1] + 0.5), None, FLAT)   # nové high v konsolidácii
    assert [o.action for o in out.orders] == [OrderAction.CANCEL, OrderAction.ENTRY]
    assert out.orders[0].order_id == first.order_id
    assert out.orders[1].plan.entry > first.plan.entry
