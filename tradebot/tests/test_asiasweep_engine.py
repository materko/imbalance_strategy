"""ASIA SWEEP 1.0: engine na syntetických 5m baroch EURUSD.

Testuje sa mechanika, nie edge: range Ázie, sweep len v okne Londýna, návrat do rangu, hĺbka sweepu,
vstupné modely pin bar a IBS imbalance, stop za sweep a cieľ RR, filter naked POC a výstup v čase.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, SizeSpec
from tradebot.strategies.asiasweep import AsiaSweepConfig, AsiaSweepEngine, EntryModel

NY = ZoneInfo("America/New_York")
EU = INSTRUMENTS["eurusd_dukascopy"]
STEP = 5 * 60_000
OKNO = MarketContext(in_trade_window=True)


def t(day: int, h: int, m: int = 0) -> int:
    """Čas New York v septembri 2025 (1. 9. je pondelok) → ms."""
    return int(datetime(2025, 9, day, h, m, tzinfo=NY).timestamp() * 1000)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


class Run:
    def __init__(self, **kw) -> None:
        base = dict(entryModel=EntryModel.PINBAR, slBuffer=SizeSpec(0.0, "atr"), rrRatio=2.0)
        base.update(kw)
        self.e = AsiaSweepEngine(AsiaSweepConfig(**base), EU, 5)
        self.t = None

    def bars(self, start: int, end: int, o: float, h: float, l: float, c: float, v: float = 100.0):
        outs = []
        ts = start
        while ts < end:
            outs.append(self.e.on_bar(Bar(ts, o, h, l, c, v), None, OKNO))
            ts += STEP
        return outs

    def one(self, ts: int, o: float, h: float, l: float, c: float, ctx=OKNO, v: float = 100.0):
        return self.e.on_bar(Bar(ts, o, h, l, c, v), None, ctx)


def asia(r: Run, day: int = 1, start_h: int = 18) -> None:
    """Pondelok `start_h`–02:00: range Ázie 20:00–00:00 je 1,10000–1,10100, potom pokoj v ňom."""
    r.bars(t(day, start_h), t(day, 20), 1.1005, 1.1008, 1.1002, 1.1005)
    r.bars(t(day, 20), t(day + 1, 0), 1.1005, 1.1010, 1.1000, 1.1005)
    r.bars(t(day + 1, 0), t(day + 1, 2, 30), 1.1005, 1.1008, 1.1002, 1.1005)


def test_range_azie():
    r = Run()
    asia(r)
    assert (r.e.range_hi, r.e.range_lo) == (1.1010, 1.1000)


def test_sweep_maxima_pin_barom_short():
    r = Run()
    asia(r)
    # 2:30 pin bar: knôt nad maximum Ázie, zavretie späť v range
    out = r.one(t(2, 2, 30), 1.1006, 1.1030, 1.1004, 1.1005)
    p = entries(out)[0].plan
    assert p.direction is Direction.SHORT
    assert p.entry == 1.1005 and p.stop_loss == 1.1030
    assert abs(p.take_profit - (1.1005 - 2 * 0.0025)) < 1e-9


def test_bez_navratu_do_rangu_sa_nevstupuje():
    r = Run()
    asia(r)
    # zavrie nad maximom (sweep bez návratu) — aj keby bol pin bar, nevstúpi sa
    assert not entries(r.one(t(2, 2, 30), 1.1012, 1.1030, 1.1010, 1.1013))
    # ďalšia sviečka zavrie späť v range ako pin bar → short
    out = r.one(t(2, 2, 35), 1.1009, 1.1028, 1.1007, 1.1008)
    assert entries(out)[0].plan.direction is Direction.SHORT


def test_prilis_hlboky_sweep_rusi_setup():
    r = Run(maxSweep=SizeSpec(0.5, "atr"))   # ATR ≈ 0,0006–0,001 → max ~0,0005
    asia(r)
    assert not entries(r.one(t(2, 2, 30), 1.1006, 1.1060, 1.1004, 1.1005))


def test_prieraz_mimo_londyna_nie_je_sweep():
    r = Run()
    asia(r)
    r.bars(t(2, 2, 30), t(2, 6), 1.1005, 1.1008, 1.1002, 1.1005)
    assert not entries(r.one(t(2, 6), 1.1006, 1.1030, 1.1004, 1.1005))   # 6:00 — po okne sweepu


def test_sweep_minima_imbalance_long():
    r = Run(entryModel=EntryModel.IMBALANCE, imbMinSize=SizeSpec(0.0, "atr"))
    asia(r)
    r.one(t(2, 2, 30), 1.1003, 1.1004, 1.0985, 1.0995)   # sweep minima, zavretie pod range
    r.one(t(2, 2, 35), 1.0995, 1.1001, 1.0994, 1.1000)
    r.one(t(2, 2, 40), 1.1000, 1.1006, 1.0999, 1.1005)   # zavretie späť v range, stredná pre imbalance
    out = r.one(t(2, 2, 45), 1.1005, 1.1012, 1.1004, 1.1010)   # low 1,1004 > high 2:35 (1,1001) = imbalance
    p = entries(out)[0].plan
    assert p.direction is Direction.LONG and p.stop_loss == 1.0985


def test_naked_poc_filter():
    kw = dict(useNpoc=True, vpStartH=17, vpEndH=19, vpRowTicks=10)
    # deň profilu 17:00–19:00 s POC na 1,0950 (pod cenou) → short smie
    r = Run(**kw)
    r.bars(t(1, 17), t(1, 19), 1.0950, 1.0951, 1.0949, 1.0950, v=1000.0)
    asia(r, start_h=19)
    assert [round(n.price, 5) for n in r.e.npocs] == [1.09495]   # riadok 1 pip, stred riadku
    assert entries(r.one(t(2, 2, 30), 1.1006, 1.1030, 1.1004, 1.1005))
    # POC nad cenou (1,1100) → short nesmie (v smere nie je naked POC)
    r = Run(**kw)
    r.bars(t(1, 17), t(1, 19), 1.1100, 1.1101, 1.1099, 1.1100, v=1000.0)
    asia(r, start_h=19)
    assert not entries(r.one(t(2, 2, 30), 1.1006, 1.1030, 1.1004, 1.1005))


def test_dotknuty_poc_nie_je_naked():
    r = Run(useNpoc=True, vpStartH=17, vpEndH=19, vpRowTicks=10)
    r.bars(t(1, 17), t(1, 19), 1.0950, 1.0951, 1.0949, 1.0950, v=1000.0)
    r.one(t(1, 19, 30), 1.0960, 1.0990, 1.0940, 1.0985)   # prejde cez POC 1,09495
    assert r.e.npocs == []


def test_zatvorenie_v_case():
    r = Run(exitH=12)
    asia(r)
    r.one(t(2, 2, 30), 1.1006, 1.1030, 1.1004, 1.1005)
    pos = MarketContext(in_trade_window=True, position_size=-1.0, open_order_ids=frozenset({"x"}))
    assert not r.one(t(2, 11, 50), 1.1000, 1.1001, 1.0999, 1.1000, ctx=pos).close_session
    assert r.one(t(2, 11, 55), 1.1000, 1.1001, 1.0999, 1.1000, ctx=pos).close_session   # zavretie 12:00
