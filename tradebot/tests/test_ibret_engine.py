"""IB RETRACE: engine na syntetických baroch (MNQ, 5m).

IB 9:30–10:30 NY má high 110 a low 100 (šírka 10). Úrovne pri longu: 0,25 → 107,5 (limitka), 0,8 → 102 (stop),
extenzia +0,5 → 115 (cieľ). Testuje sa prieraz, limitka, jej zrušenie, okno prierazu, deň v týždni a koniec dňa.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.config import ConfigError
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.ibret import EntryMode, IbRetConfig, IbRetEngine, TpMode

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
STEP = 5 * 60_000
OKNO = MarketContext(in_trade_window=True)
TUE = datetime(2025, 9, 2, tzinfo=NY)           # utorok


def at(day: datetime, hh: int, mm: int) -> int:
    return int(day.replace(hour=hh, minute=mm).timestamp() * 1000)


def b(ms: int, o: float, h: float, lo: float, c: float) -> Bar:
    return Bar(time=ms, open=o, high=h, low=lo, close=c, volume=10.0)


def engine(**kw) -> IbRetEngine:
    return IbRetEngine(IbRetConfig(**kw), MNQ, 5)


def ib(e: IbRetEngine, day: datetime = TUE, ctx: MarketContext = OKNO) -> None:
    """9:30–10:25: dvanásť 5m barov, high 110, low 100."""
    for i in range(12):
        t = at(day, 9, 30) + i * STEP
        e.on_bar(b(t, 105, 110 if i == 3 else 106, 100 if i == 7 else 104, 105), ctx=ctx)


def orders(out, action):
    return [o for o in out.orders if o.action is action]


def test_prieraz_hore_limitka_na_navrate_stop_za_max_retracementom():
    e = engine()
    ib(e)
    out = e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO)
    (o,) = orders(out, OrderAction.ENTRY)
    assert o.order_type is OrderType.LIMIT and o.direction is Direction.LONG
    assert (o.plan.entry, o.plan.stop_loss, o.plan.take_profit) == (107.5, 102.0, 115.0)
    assert o.plan.qty == MNQ.qty_for_risk(250.0, 5.5)
    assert {d.kind for d in out.drawings} >= {"tp_box", "sl_box", "ibret_entry"}


def test_prieraz_dole_zrkadlo():
    e = engine()
    ib(e)
    (o,) = orders(e.on_bar(b(at(TUE, 10, 30), 101, 101.5, 98.5, 99), ctx=OKNO), OrderAction.ENTRY)
    assert o.direction is Direction.SHORT
    assert (o.plan.entry, o.plan.stop_loss, o.plan.take_profit) == (102.5, 108.0, 95.0)


def test_breakout_market_a_rr_ciel():
    e = engine(entryMode=EntryMode.BREAKOUT, tpMode=TpMode.RR, rr=1.0)
    ib(e)
    (o,) = orders(e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO), OrderAction.ENTRY)
    assert o.order_type is OrderType.MARKET and o.plan.entry == 111 and o.plan.stop_loss == 102.0
    assert o.plan.take_profit == 120.0


def test_maly_rr_obchod_vynecha():
    e = engine(entryMode=EntryMode.BREAKOUT, tpExt=0.3)   # vstup 111, stop 102, cieľ 113 → RR 0,22
    ib(e)
    assert not orders(e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO), OrderAction.ENTRY)


def test_limitka_sa_zrusi_ked_cena_dojde_do_ciela_bez_navratu():
    e = engine()
    ib(e)
    e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO)
    assert not e.on_bar(b(at(TUE, 10, 35), 111, 113, 110, 112.5), ctx=OKNO).orders
    (c,) = orders(e.on_bar(b(at(TUE, 10, 40), 112.5, 115.25, 112, 115), ctx=OKNO), OrderAction.CANCEL)
    assert c.reason == "cieľ bez návratu"
    assert not e.on_bar(b(at(TUE, 10, 45), 115, 116, 106, 107), ctx=OKNO).orders   # deň je rozhodnutý


def test_limitka_sa_zrusi_pri_prieraze_druhej_strany_a_o_last_entry():
    e = engine()
    ib(e)
    e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO)
    (c,) = orders(e.on_bar(b(at(TUE, 10, 35), 111, 111, 99, 99.5), ctx=OKNO), OrderAction.CANCEL)
    assert c.reason == "prieraz druhej strany IB"
    e2 = engine(lastEntry=1040)
    ib(e2)
    e2.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO)
    (c2,) = orders(e2.on_bar(b(at(TUE, 10, 35), 111, 112, 110, 111), ctx=OKNO), OrderAction.CANCEL)
    assert c2.reason == "koniec vstupov"


def test_vyplnena_limitka_sa_uz_nerusi_a_pozicia_sa_zavrie_o_16():
    e = engine()
    ib(e)
    (o,) = orders(e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO), OrderAction.ENTRY)
    v = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({o.order_id}))
    assert not orders(e.on_bar(b(at(TUE, 10, 35), 111, 113, 107, 108), ctx=v), OrderAction.CANCEL)
    assert not e.on_bar(b(at(TUE, 15, 50), 110, 111, 109, 110), ctx=v).orders
    out = e.on_bar(b(at(TUE, 15, 55), 110, 111, 109, 110), ctx=v)
    (z,) = orders(out, OrderAction.CLOSE)
    assert z.order_id == o.order_id and z.reason == "koniec 1600 NY" and out.close_session


def test_okno_prierazu_a_prvy_prieraz_rozhoduje():
    e = engine(breakFrom=1035)
    ib(e)
    assert not e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO).orders     # prieraz pred oknom
    assert not e.on_bar(b(at(TUE, 10, 35), 111, 112, 110, 111.5), ctx=OKNO).orders      # deň je rozhodnutý


def test_den_v_tyzdni_a_smer():
    e = engine(tradeTue=False)
    ib(e)
    assert not e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO).orders
    e2 = engine(tradeDirection="Short only")
    ib(e2)
    assert not e2.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO).orders


def test_novy_den_zrusi_limitku_a_config_kontroluje_urovne():
    e = engine(lastEntry=2359)
    ib(e)
    e.on_bar(b(at(TUE, 10, 30), 109, 111.5, 108.5, 111), ctx=OKNO)
    wed = datetime(2025, 9, 3, tzinfo=NY)
    (c,) = orders(e.on_bar(b(at(wed, 0, 0), 111, 111.5, 110.5, 111), ctx=OKNO), OrderAction.CANCEL)
    assert c.reason == "nový deň"
    with pytest.raises(ConfigError, match="slRetr"):
        IbRetConfig(entryRetr=0.5, slRetr=0.4)
