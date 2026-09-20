"""Breakout: engine na syntetických baroch.

Testuje sa mechanika, nie edge: či sa otváracia sviečka vezme z informatívneho TF, či
prerazenie musí naozaj **zavrieť** za hranicou, čo urobí market a čo limit príkaz, kam
ide stop a čo sa stane na konci seansy.

Osobitne sa testuje to, kvôli čomu tu informatívny TF vôbec je: že 1m, 2m aj 3m graf
dostanú tú istú otváraciu sviečku.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradebot.core import BTCUSDT_BINANCE, Bar, MarketContext, OrderAction
from tradebot.core.types import Direction, OrderType
from tradebot.strategies.breakout import (BreakoutConfig, BreakoutEngine, OpeningFeeder,
                                          OrderKind, TradeDirection)

NY = ZoneInfo("America/New_York")
#: utorok 2025-09-02, 9:30 New York — vnútri pracovného týždňa, inak by `weekdaysOnly`
#: obchody odmietol a testy by merali nesprávnu vec.
OPEN_MS = int(datetime(2025, 9, 2, 9, 30, tzinfo=NY).timestamp() * 1000)
MIN = 60_000
OKNO = MarketContext(in_trade_window=True)

#: otváracia sviečka: high 100.6, low 99.4 — obe hranice ďaleko od seba, nech sa stop
#: nezasekne na `tick_size * 2`
OPEN_HIGH, OPEN_LOW = 100.6, 99.4


def bar(ts: int, o=100.0, h=100.2, low=99.8, c=100.0, v=10.0) -> Bar:
    return Bar(time=ts, open=o, high=h, low=low, close=c, volume=v)


def _engine(tf: int = 3, **kw) -> tuple[BreakoutEngine, OpeningFeeder]:
    cfg = BreakoutConfig(**kw)
    return BreakoutEngine(cfg, BTCUSDT_BINANCE, tf), OpeningFeeder(cfg, tf)


def _opening_candle(feeder: OpeningFeeder) -> None:
    """Otváracia sviečka tak, ako ju dodá adaptér: uzavretý bar informatívneho TF."""
    feeder.feed(bar(OPEN_MS, o=100.0, h=OPEN_HIGH, low=OPEN_LOW, c=100.0, v=50.0))


def _step(engine: BreakoutEngine, feeder: OpeningFeeder, b: Bar,
          ctx: MarketContext = OKNO):
    """Jeden bar grafu presne tak, ako ho podá runner: bar + okno z feedera + kontext."""
    return engine.on_bar(b, feeder.window_for(b.time), ctx)


def warm(engine: BreakoutEngine, feeder: OpeningFeeder, tf: int = 3, bars: int = 60) -> None:
    """Bary pred otvorením seansy — naplnia ATR a SMA objemu."""
    step = tf * MIN
    for i in range(bars, 0, -1):
        _step(engine, feeder, bar(OPEN_MS - i * step))


def _after_open(tf: int = 3) -> int:
    """Prvý bar grafu, na ktorom sa už smie obchodovať (otváracia sviečka je uzavretá)."""
    step = tf * MIN
    ts = OPEN_MS
    while ts - OPEN_MS < 5 * MIN:
        ts += step
    return ts


# --------------------------------------------------------------------------- #


def test_defaults_a_predhistoria():
    cfg = BreakoutConfig()
    assert cfg.openingMinutes.minutes == 5 and cfg.openingMinutes.timeframe == "5m"
    assert cfg.rrRatio == 1.0 and cfg.orderType is OrderKind.MARKET
    engine, _ = _engine()
    assert engine.required_history == cfg.atrLen + cfg.volSmaLen + 16


def test_otvaracia_sviecka_pride_z_informativneho_tf():
    engine, feeder = _engine()
    warm(engine, feeder)
    _opening_candle(feeder)
    out = _step(engine, feeder, bar(OPEN_MS))
    assert engine._state.high is None, "na bare 9:30 sa 5m sviečka ešte nezavrela"
    out = _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    assert (engine._state.high, engine._state.low) == (OPEN_HIGH, OPEN_LOW)
    assert {d.kind.value for d in out.drawings} >= {"bo_box", "bo_high", "bo_low"}


def test_prerazenie_hore_da_market_order_so_stopom_pod_sviecku():
    engine, feeder = _engine()
    warm(engine, feeder)
    _opening_candle(feeder)
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    ts = _after_open()
    out = _step(engine, feeder, bar(ts, o=100.5, h=101.0, low=100.4, c=100.9))

    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    plan = entries[0].plan
    assert entries[0].order_type is OrderType.MARKET
    assert plan.direction is Direction.LONG and plan.entry == pytest.approx(100.9)
    assert plan.stop_loss == pytest.approx(OPEN_LOW), "stop ide pod low otváracej sviečky"
    assert plan.take_profit == pytest.approx(100.9 + (100.9 - OPEN_LOW))  # rrRatio = 1


def test_knot_nad_hranicu_nestaci_musi_zavriet():
    """Zadanie hovorí „prerazenie a **zatvorenie** sviečky" — prepichnutie knôtom nie je signál."""
    engine, feeder = _engine()
    warm(engine, feeder)
    _opening_candle(feeder)
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    out = _step(engine, feeder, bar(_after_open(), o=100.2, h=101.5, low=100.1, c=100.3))
    assert [o for o in out.orders if o.action is OrderAction.ENTRY] == []


def test_limit_prikaz_da_limitku_na_prerazenu_hranicu():
    engine, feeder = _engine(orderType=OrderKind.LIMIT)
    warm(engine, feeder)
    _opening_candle(feeder)
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    out = _step(engine, feeder, bar(_after_open(), o=100.5, h=101.0, low=100.4, c=100.9))

    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    assert entries[0].order_type is OrderType.LIMIT
    assert entries[0].plan.entry == pytest.approx(OPEN_HIGH), "limitka čaká na retest hranice"
    # rovnaký stop, ale kratší -> menšie riziko na kus než pri markete
    assert entries[0].plan.sl_distance < OPEN_HIGH + 0.3 - OPEN_LOW


def test_market_a_limit_sa_lisia_len_cenou_vstupu():
    """Ten istý signál, dva príkazy — zrkadlový test, aby sa vetvy nemohli stotožniť."""
    plany = {}
    for kind in (OrderKind.MARKET, OrderKind.LIMIT):
        engine, feeder = _engine(orderType=kind)
        warm(engine, feeder)
        _opening_candle(feeder)
        _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
        out = _step(engine, feeder, bar(_after_open(), o=100.5, h=101.0, low=100.4, c=100.9))
        plany[kind] = [o for o in out.orders if o.action is OrderAction.ENTRY][0].plan
    assert plany[OrderKind.MARKET].entry != plany[OrderKind.LIMIT].entry
    assert plany[OrderKind.MARKET].stop_loss == plany[OrderKind.LIMIT].stop_loss


def test_nevyplnena_limitka_sa_po_uplynuti_platnosti_zrusi():
    engine, feeder = _engine(orderType=OrderKind.LIMIT, limitValidMinutes=6)
    warm(engine, feeder)
    _opening_candle(feeder)
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    ts = _after_open()
    out = _step(engine, feeder, bar(ts, o=100.5, h=101.0, low=100.4, c=100.9))
    order_id = [o for o in out.orders if o.action is OrderAction.ENTRY][0].order_id

    zrusene = []
    for i in range(1, 6):  # 6 minút platnosti na 3m grafe = 2 bary
        out = _step(engine, feeder, bar(ts + i * 3 * MIN, c=100.7))
        zrusene += [o.order_id for o in out.orders if o.action is OrderAction.CANCEL]
    assert zrusene == [order_id]


def test_short_only_ignoruje_prerazenie_hore():
    engine, feeder = _engine(tradeDirection=TradeDirection.SHORT_ONLY)
    warm(engine, feeder)
    _opening_candle(feeder)
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    out = _step(engine, feeder, bar(_after_open(), o=100.5, h=101.0, low=100.4, c=100.9))
    assert [o for o in out.orders if o.action is OrderAction.ENTRY] == []


def test_prerazenie_dole_da_short_so_stopom_nad_sviecku():
    engine, feeder = _engine()
    warm(engine, feeder)
    _opening_candle(feeder)
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    out = _step(engine, feeder, bar(_after_open(), o=99.5, h=99.6, low=99.0, c=99.1))
    plan = [o for o in out.orders if o.action is OrderAction.ENTRY][0].plan
    assert plan.direction is Direction.SHORT
    assert plan.stop_loss == pytest.approx(OPEN_HIGH)
    assert plan.take_profit == pytest.approx(99.1 - (OPEN_HIGH - 99.1))


def test_okno_na_vstup_zavrie_neskore_prerazenie():
    engine, feeder = _engine(entryWindowMinutes=30)
    warm(engine, feeder)
    _opening_candle(feeder)
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    neskoro = OPEN_MS + 45 * MIN
    out = _step(engine, feeder, bar(neskoro, o=100.5, h=101.0, low=100.4, c=100.9))
    assert [o for o in out.orders if o.action is OrderAction.ENTRY] == []


def test_koniec_seansy_zatvori_otvorenu_poziciu():
    engine, feeder = _engine()
    warm(engine, feeder)
    _opening_candle(feeder)
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    koniec = int(datetime(2025, 9, 2, 15, 57, tzinfo=NY).timestamp() * 1000)
    ctx = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"bo:1"}))
    out = _step(engine, feeder, bar(koniec), ctx)
    assert out.close_session is True
    assert [o.action for o in out.orders] == [OrderAction.CLOSE]


def test_bez_informativneho_tf_nevznikne_ziadny_obchod():
    """Bez otváracej sviečky nemá stratégia úroveň — mlčí, nedomýšľa si ju z barov grafu."""
    engine, feeder = _engine()
    warm(engine, feeder)   # feeder zámerne nedostal ani jeden HTF bar
    out = _step(engine, feeder, bar(_after_open(), o=100.5, h=101.0, low=100.4, c=100.9))
    assert out.orders == [] and engine._state.high is None


def test_filter_sirky_preskoci_prilis_uzku_sviecku():
    engine, feeder = _engine(minRangePct=1.0)   # sviečka má ~1,19 %, tesne prejde
    warm(engine, feeder)
    feeder.feed(bar(OPEN_MS, o=100.0, h=100.1, low=99.9, c=100.0))  # 0,2 % — neprejde
    _step(engine, feeder, bar(OPEN_MS + 3 * MIN))
    assert engine._state.seen is True and engine._state.ok is False
    out = _step(engine, feeder, bar(_after_open(), o=100.05, h=100.4, low=100.0, c=100.3))
    assert [o for o in out.orders if o.action is OrderAction.ENTRY] == []


@pytest.mark.parametrize("tf", [1, 2, 3])
def test_1m_2m_aj_3m_graf_vidia_tu_istu_otvaraciu_sviecku(tf):
    """Toto je dôvod, prečo je sviečka z informatívneho TF a nie z barov grafu.

    5 sa dvomi ani tromi nedelí — z barov 3m grafu by vyšlo okno 9:30–9:36, teda o pätinu
    širšia „otváracia sviečka" než tá, na ktorú sa pozerá obchodník na 5m grafe.
    """
    engine, feeder = _engine(tf=tf)
    warm(engine, feeder, tf=tf)
    _opening_candle(feeder)
    ts = OPEN_MS
    while engine._state.high is None and ts < OPEN_MS + 20 * MIN:
        _step(engine, feeder, bar(ts))
        ts += tf * MIN
    assert (engine._state.high, engine._state.low) == (OPEN_HIGH, OPEN_LOW)
    # a nikdy nie skôr, než sa tá sviečka naozaj uzavrela
    assert ts - tf * MIN + tf * MIN >= OPEN_MS + 5 * MIN
