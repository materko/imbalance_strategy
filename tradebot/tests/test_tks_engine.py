"""TKS 1.0: mechanika signálu (N sviečok za hranicou, spotrebovanie a nové nabitie), SL na najbližší swing,
TP v RR, limit za seansu a výpočet NQ Kompasu (zložky na syntetickej seanse)."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction
from tradebot.strategies.tks import Kompas, TksConfig, TksEngine

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
M3 = 180_000
FLAT = MarketContext(in_trade_window=True)
LONGPOS = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"x"}))
DAY = datetime(2025, 9, 3, tzinfo=NY)          # streda


def t(h: int, m: int, day: datetime = DAY) -> int:
    return int(day.replace(hour=h, minute=m).timestamp() * 1000)


def bar(ts: int, c: float, hi: float | None = None, lo: float | None = None) -> Bar:
    return Bar(ts, c, c + 1 if hi is None else hi, c - 1 if lo is None else lo, c, 100.0)


def engine_with(values: list[float | None], **kw) -> tuple[TksEngine, list]:
    """Engine, ktorému Kompas vráti dané hodnoty (po jednej na bar) — testuje sa len mechanika."""
    e = TksEngine(TksConfig(**kw), MNQ, 3)
    it = iter(values)
    e.kompas.push = lambda b: next(it)           # type: ignore[method-assign]
    e.kompas.rth = True
    e.kompas.day = (2025, 9, 3)
    return e, []


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def feed(e: TksEngine, prices, ctx=FLAT, start=(10, 0)):
    outs = []
    ts = t(*start)
    for p in prices:
        hi, lo = (p, p) if not isinstance(p, tuple) else p[1:]
        c = p if not isinstance(p, tuple) else p[0]
        outs.append(e.on_bar(Bar(ts, c, max(c, hi) + 1, min(c, lo) - 1, c, 100.0), None, ctx))
        ts += M3
    return outs


def test_short_po_troch_sviečkach_pod_hranicou_sl_na_swing_high_tp_1_1():
    # ceny: swing high 120 v strede (bar 3), potom klesanie; Kompas pod 35 na posledných 3 baroch
    prices = [100, 110, 115, 120, 115, 110, 105, 100, 95]
    e, _ = engine_with([50, 50, 50, 50, 50, 50, 30, 30, 30])
    outs = feed(e, prices)
    assert not any(entries(o) for o in outs[:-1])
    oi = entries(outs[-1])[0]
    assert oi.direction is Direction.SHORT
    assert oi.plan.stop_loss == MNQ.round_price(121)          # swing high (high baru = close + 1)
    assert oi.plan.take_profit == MNQ.round_price(95 - (121 - 95))
    assert oi.plan.qty == 1.0


def test_long_zrkadlovo_a_rr():
    prices = [100, 90, 85, 80, 85, 90, 95, 100, 105]
    e, _ = engine_with([50] * 6 + [70, 70, 70], rrRatio=0.5)
    oi = entries(feed(e, prices)[-1])[0]
    assert oi.direction is Direction.LONG
    assert oi.plan.stop_loss == MNQ.round_price(79)
    assert oi.plan.take_profit == MNQ.round_price(105 + 0.5 * (105 - 79))


def test_signal_sa_spotrebuje_a_nabije_az_po_navrate_nad_hranicu():
    prices = [100, 110, 115, 120, 115, 110, 105, 100, 95, 94, 93, 92, 91, 90, 89]
    vals = [50] * 6 + [30, 30, 30, 30, 30] + [40] + [30, 30, 30]
    e, _ = engine_with(vals)
    outs = feed(e, prices)
    n = [i for i, o in enumerate(outs) if entries(o)]
    assert n == [8, 14]                       # 2. vstup až po návrate nad 35 a ďalších 3 sviečkach pod


def test_pozicia_a_limit_za_seansu():
    prices = [100, 110, 115, 120, 115, 110, 105, 100, 95]
    e, _ = engine_with([50] * 6 + [30, 30, 30])
    assert not any(entries(o) for o in feed(e, prices, ctx=LONGPOS))     # pozícia otvorená → nevstupuje
    e, _ = engine_with([50] * 6 + [30, 30, 30] + [40] + [30, 30, 30], maxTradesPerSession=1)
    outs = feed(e, prices + [94, 93, 92, 91])
    assert sum(1 for o in outs if entries(o)) == 1


def test_kompas_zlozky_na_syntetickej_seanse():
    k = Kompas(3, lookback=14)
    day0 = datetime(2025, 8, 4, tzinfo=NY)
    d, n = day0, 0
    while n < 8:                                               # 8 dní: každá sviečka 0,1 % nad open
        if d.weekday() < 5:
            for i in range(130):
                ts = int((d.replace(hour=9, minute=30) + timedelta(minutes=3 * i)).timestamp() * 1000)
                k.push(Bar(ts, 20000.0, 20025.0, 19995.0, 20000.0 * 1.001, 100.0))   # open dňa 20 000
            n += 1
        d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    # noc 18:00 → 9:30 v range 19 990–20 010, potom seansa rastie a zatvára pri high s objemom
    ev = d - timedelta(days=1)
    for i in range(20):
        k.push(bar(int(ev.replace(hour=18, minute=0).timestamp() * 1000) + i * M3, 20000.0, 20010.0, 19990.0))
    vals = []
    for i in range(10):
        c = 20000.0 + 15 * (i + 1)
        vals.append(k.push(Bar(int((d.replace(hour=9, minute=30) + timedelta(minutes=3 * i)).timestamp() * 1000),
                               c - 10, c, c - 12, c, 100.0)))
    assert vals[0] is not None and vals[-1] > 80                # silný trend dňa → Kompas vysoko


def test_casove_okno_a_prestavka():
    prices = [100, 110, 115, 120, 115, 110, 105, 100, 95]
    e, _ = engine_with([50] * 6 + [30, 30, 30], entryStartMin=60)        # signál o 10:27 (k = 57) → pred oknom
    e.kompas.k_close = 57
    outs = []
    ts = t(10, 0)
    for p in prices:
        outs.append(e.on_bar(Bar(ts, p, p + 1, p - 1, p, 100.0), None, FLAT)); ts += M3
    # k_close nastavuje Kompas; pri náhradnom Kompase ostáva 57 → mimo okna
    assert not any(entries(o) for o in outs)
    e, _ = engine_with([50] * 6 + [30, 30, 30], pauseFromMin=50, pauseToMin=70)
    e.kompas.k_close = 57
    assert not any(entries(o) for o in feed(e, prices))
    e, _ = engine_with([50] * 6 + [30, 30, 30], pauseFromMin=0, pauseToMin=0)
    e.kompas.k_close = 57
    assert entries(feed(e, prices)[-1])


def test_sl_body_atr_a_strop():
    prices = [100, 110, 115, 120, 115, 110, 105, 100, 95]
    e, _ = engine_with([50] * 6 + [30, 30, 30], slMode="points", slPoints=12)
    e.kompas.k_close = 57
    oi = entries(feed(e, prices)[-1])[0]
    assert oi.plan.stop_loss == MNQ.round_price(107) and oi.plan.take_profit == MNQ.round_price(83)
    e, _ = engine_with([50] * 6 + [30, 30, 30], maxSlPoints=20)          # swing SL 121 je 26 bodov → vynechá
    e.kompas.k_close = 57
    assert not any(entries(o) for o in feed(e, prices))
    e, _ = engine_with([50] * 6 + [30, 30, 30], slMode="atr", slAtrMult=2.0, atrLen=3)
    e.kompas.k_close = 57
    oi = entries(feed(e, prices)[-1])[0]
    assert oi.plan.stop_loss > 95
