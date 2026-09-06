"""Testy stavového automatu STATE 0-5, hľadania gapu, patternov a risku."""

from __future__ import annotations

import pytest

from tradebot.core import (
    MNQ,
    Bar,
    BarHistory,
    Direction,
    IBSConfig,
    MarketContext,
    OrderAction,
    StateMachine,
    Zone,
    ZoneBook,
    ZoneState,
    build_trade_plan,
    find_imbalance,
    is_engulfing,
    is_pin_bar,
    swing_stop_loss,
)
from tradebot.core.types import OrderType

T0 = 1_756_684_800_000
MIN3 = 180_000


def bar(i: int, o: float, h: float, low: float, c: float, v: float = 100.0) -> Bar:
    return Bar(time=T0 + i * MIN3, open=o, high=h, low=low, close=c, volume=v)


def feed(history: BarHistory, *bars: Bar) -> BarHistory:
    for b in bars:
        history.append(b)
    return history


@pytest.fixture
def cfg() -> IBSConfig:
    # Len IMB model, aby testy stavov nerušili Pin Bar / Engulfing vetvy.
    return IBSConfig(enableImbEntry=True, enablePinBarEntry=False, enableEngulfingEntry=False)


@pytest.fixture
def ctx() -> MarketContext:
    return MarketContext(in_trade_window=True)


# --------------------------------------------------------------------------- #
# Pin Bar / Engulfing
# --------------------------------------------------------------------------- #


def test_bullish_pin_bar_detected(cfg):
    # dlhy dolny knot, telo hore: rng 10, telo 1, dolny knot 9
    b = bar(0, 109, 110, 100, 110)
    assert is_pin_bar(b, Direction.LONG, cfg, MNQ) is True


def test_pin_bar_rejected_when_body_too_big(cfg):
    b = bar(0, 101, 110, 100, 109)  # telo 8, knot 1
    assert is_pin_bar(b, Direction.LONG, cfg, MNQ) is False


def test_pin_bar_rejected_when_body_not_at_the_edge(cfg):
    # dolny knot je dost dlhy, ale nad telom zostal velky horny knot
    b = bar(0, 104, 110, 100, 104.5)
    assert is_pin_bar(b, Direction.LONG, cfg, MNQ) is False


def test_pin_bar_rejected_when_range_too_small(cfg):
    b = bar(0, 100.9, 101, 100, 101)  # rng 1 < pbMinRangePoints 2
    assert is_pin_bar(b, Direction.LONG, cfg, MNQ) is False


def test_bearish_pin_bar_needs_upper_wick(cfg):
    b = bar(0, 101, 110, 100, 100.5)  # dlhy HORNY knot
    assert is_pin_bar(b, Direction.SHORT, cfg, MNQ) is True
    assert is_pin_bar(b, Direction.LONG, cfg, MNQ) is False


def test_engulfing_is_an_outlier_by_range(cfg):
    """Nie geometricky engulfing - rozhoduje rozsah voci priemeru poslednych 10 sviecok."""
    h = BarHistory()
    for i in range(10):
        h.append(bar(i, 100, 101, 99, 100.5))  # rozsah 2
    h.append(bar(10, 100, 106, 100, 105))  # rozsah 6 >= 2 x 2
    assert is_engulfing(h, Direction.LONG, cfg, MNQ) is True


def test_engulfing_rejects_average_sized_candle(cfg):
    h = BarHistory()
    for i in range(10):
        h.append(bar(i, 100, 101, 99, 100.5))
    h.append(bar(10, 100, 101.5, 99.5, 101))
    assert is_engulfing(h, Direction.LONG, cfg, MNQ) is False


def test_engulfing_respects_direction(cfg):
    h = BarHistory()
    for i in range(10):
        h.append(bar(i, 100, 101, 99, 100.5))
    h.append(bar(10, 100, 106, 100, 105))  # bullish
    assert is_engulfing(h, Direction.SHORT, cfg, MNQ) is False


# --------------------------------------------------------------------------- #
# Hľadanie gapu
# --------------------------------------------------------------------------- #


def test_long_zone_looks_for_a_bearish_gap(cfg):
    """Zóna typu LONG hľadá BEARISH gap - ten sa má vyplniť smerom nahor."""
    h = BarHistory()
    # far[lb+2] low 120 ; mid[lb+1] nad zonou ; near[lb] high 110 -> gap 10
    feed(
        h,
        bar(0, 125, 126, 120, 121),  # far
        bar(1, 118, 119, 112, 113),  # mid - nad zonou (open 118 > top 100)
        bar(2, 109, 110, 105, 106),  # near, high 110 < far.low 120
    )
    hit = find_imbalance(h, 100, 90, Direction.LONG, cfg, MNQ, zone_created_bar_index=0)
    assert hit is not None
    assert hit.offset == 1
    assert hit.entry_price == 118  # Pine zImbOpenA = open prostrednej sviecky


def test_gap_below_min_size_is_ignored(cfg):
    h = BarHistory()
    feed(
        h,
        bar(0, 125, 126, 120, 121),
        bar(1, 118, 119, 112, 113),
        bar(2, 118, 119.5, 115, 116),  # high 119.5 vs far.low 120 -> gap 0.5 < 2.5
    )
    assert find_imbalance(h, 100, 90, Direction.LONG, cfg, MNQ, zone_created_bar_index=0) is None


def test_gap_too_far_from_zone_is_ignored(cfg):
    cfg.imbMaxDistTicks = 4  # 4 ticky x 0.25 = 1.0 bodu
    h = BarHistory()
    feed(
        h,
        bar(0, 125, 126, 120, 121),
        bar(1, 118, 119, 112, 113),  # low 112, top zony 100 -> vzdialenost 12
        bar(2, 109, 110, 105, 106),
    )
    assert find_imbalance(h, 100, 90, Direction.LONG, cfg, MNQ, zone_created_bar_index=0) is None


def test_gap_before_zone_creation_is_ignored(cfg):
    h = BarHistory()
    feed(
        h,
        bar(0, 125, 126, 120, 121),
        bar(1, 118, 119, 112, 113),
        bar(2, 109, 110, 105, 106),
    )
    assert find_imbalance(h, 100, 90, Direction.LONG, cfg, MNQ, zone_created_bar_index=99) is None


def test_nearest_gap_wins(cfg):
    """Pri viacerych kandidatoch vyhrava ten najblizsie k zone."""
    h = BarHistory()
    feed(
        h,
        bar(0, 145, 146, 140, 141),
        bar(1, 138, 139, 132, 133),  # vzdialeny gap (low 132)
        bar(2, 129, 130, 125, 126),
        bar(3, 125, 126, 120, 121),
        bar(4, 118, 119, 105, 106),  # blizsi gap (low 105)
        bar(5, 100, 103, 99, 100),
    )
    hit = find_imbalance(h, 100, 90, Direction.LONG, cfg, MNQ, zone_created_bar_index=0)
    assert hit is not None
    assert hit.open == 118


# --------------------------------------------------------------------------- #
# Risk
# --------------------------------------------------------------------------- #


def test_swing_stop_loss_takes_the_lowest_low_plus_buffer(cfg):
    h = BarHistory()
    feed(h, bar(0, 100, 101, 95, 100), bar(1, 100, 101, 92, 100), bar(2, 100, 101, 97, 100))
    sl = swing_stop_loss(h, Direction.LONG, cfg, MNQ, zone_top=105, zone_bot=90)
    assert sl == pytest.approx(92 - 2 * 0.25)  # slBufferTicks=2, tick 0.25


def test_swing_stop_loss_for_short_takes_the_highest_high(cfg):
    h = BarHistory()
    feed(h, bar(0, 100, 105, 99, 100), bar(1, 100, 108, 99, 100))
    sl = swing_stop_loss(h, Direction.SHORT, cfg, MNQ, zone_top=105, zone_bot=90)
    assert sl == pytest.approx(108 + 0.5)


def test_trade_plan_take_profit_uses_rr_ratio(cfg):
    cfg.rrRatio = 2.0
    plan = build_trade_plan(Direction.LONG, entry=100.0, stop_loss=90.0, cfg=cfg, inst=MNQ)
    assert plan.sl_distance == 10.0
    assert plan.take_profit == 120.0
    assert plan.risk_reward == pytest.approx(2.0)


def test_short_trade_plan_is_mirrored(cfg):
    plan = build_trade_plan(Direction.SHORT, entry=100.0, stop_loss=110.0, cfg=cfg, inst=MNQ)
    assert plan.sl_distance == 10.0
    assert plan.take_profit == 90.0


def test_trailing_is_absent_when_disabled(cfg):
    assert build_trade_plan(Direction.LONG, 100.0, 90.0, cfg, MNQ).trailing is None


def test_trailing_is_computed_in_both_units(cfg):
    """Trailing sa drží v bodoch aj v tickoch - ticky kvôli porovnaniu s TradingView."""
    cfg.enableTrailing = True
    plan = build_trade_plan(Direction.LONG, 100.0, 90.0, cfg, MNQ)
    tr = plan.trailing
    assert tr is not None
    assert tr.activation_price_distance == pytest.approx(10.0)  # 1.0R z 10 bodov
    assert tr.offset_price_distance == pytest.approx(5.0)  # 0.5R
    assert tr.activation_ticks == pytest.approx(40.0)  # 10 / 0.25


# --------------------------------------------------------------------------- #
# Stavový automat
# --------------------------------------------------------------------------- #


def make_zone(book: ZoneBook, direction=Direction.LONG, top=100.0, bot=90.0) -> Zone:
    z = Zone(
        uid=0, direction=direction, top=top, bot=bot,
        created_ms=T0, confirmed_ms=T0, expires_ms=T0 + 6 * 3_600_000,
        created_bar_index=0,
    )
    book.zones.append(z)
    return z


@pytest.fixture
def machine(cfg):
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    return StateMachine(cfg, MNQ, book), book


def test_zone_is_touched_only_from_the_correct_side(machine, ctx):
    sm, book = machine
    z = make_zone(book)
    h = BarHistory()
    # cena celkom nad zonou - ziadny dotyk
    h.append(bar(0, 120, 125, 115, 120))
    sm.on_bar(h.current, h, ctx)
    assert z.touched is False

    # sviecka pretne horny okraj zony -> dotyk
    h.append(bar(1, 105, 106, 95, 99))
    sm.on_bar(h.current, h, ctx)
    assert z.touched is True


def test_zone_invalidated_when_price_falls_through(machine, ctx):
    sm, book = machine
    z = make_zone(book)
    h = BarHistory()
    h.append(bar(0, 105, 106, 95, 99))  # dotyk
    sm.on_bar(h.current, h, ctx)
    h.append(bar(1, 95, 96, 85, 86))  # low 85 < bot 90
    sm.on_bar(h.current, h, ctx)
    assert z.state == ZoneState.INVALID
    assert z.used is True


def test_state1_times_out(cfg, ctx):
    cfg.state1MaxBars = 2
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    sm = StateMachine(cfg, MNQ, book)
    z = make_zone(book)
    z.state = ZoneState.GAP_FOUND
    z.imb_open = 118.0
    z.imb_body_top = 118.0
    z.imb_body_bot = 113.0

    h = BarHistory()
    for i in range(5):
        h.append(bar(i, 95, 96, 94, 95))  # ani vystup, ani prienik
        if z.state_bar_index is None:
            z.state_bar_index = h.bar_index
        sm.on_bar(h.current, h, ctx)

    assert z.state == ZoneState.INVALID


def test_full_long_sequence_reaches_an_order(cfg, ctx):
    """0 -> 1 -> 2 -> 3 -> 4/5: gap, výstup zo zóny, potvrdenie, retest, order."""
    cfg.state3MaxBars = 5
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    sm = StateMachine(cfg, MNQ, book)
    z = make_zone(book, top=100.0, bot=90.0)
    h = BarHistory()
    intents = []

    seq = [
        bar(0, 125, 126, 120, 121),   # far  - stavia gap
        bar(1, 118, 119, 112, 113),   # mid  - nad zonou
        bar(2, 105, 106, 95, 99),     # near - dotyk zony + gap je kompletny
        # POZN: high 112 je zamerne - keby bolo nizsie, vznikol by DRUHY, blizsi gap
        # a re-entry vetva by prepla vstup na neho (co je spravne spravanie, len by
        # tento test uz netestoval to, co ma).
        bar(3, 99, 112, 98, 100.5),   # STATE1 -> 2 (high > top, low <= top)
        bar(4, 101, 122, 101, 121),   # STATE2 -> 3 (close > imb body top + 1 tick)
        bar(5, 121, 122, 117, 118),   # STATE3 -> 4 (low <= imb open 118) -> order
    ]
    for b in seq:
        h.append(b)
        intents += sm.on_bar(b, h, ctx)

    assert z.state == ZoneState.ORDER_PENDING
    entries = [i for i in intents if i.action is OrderAction.ENTRY]
    assert len(entries) == 1
    plan = entries[0].plan
    assert plan.direction is Direction.LONG
    assert plan.entry == 118.0
    assert plan.stop_loss < plan.entry < plan.take_profit
    assert entries[0].order_type is OrderType.LIMIT
    assert entries[0].order_id == "LONG_0"


def test_state3_waits_for_the_trade_window(cfg):
    """Retest mimo trade okna nesmie spustiť order."""
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    sm = StateMachine(cfg, MNQ, book)
    z = make_zone(book)
    z.state = ZoneState.CONFIRMED
    z.imb_open = 118.0
    h = BarHistory()
    h.append(bar(0, 121, 122, 117, 118))
    z.state_bar_index = h.bar_index

    sm.on_bar(h.current, h, MarketContext(in_trade_window=False))
    assert z.state == ZoneState.CONFIRMED


def _ready_zone(cfg, direction=Direction.LONG):
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    sm = StateMachine(cfg, MNQ, book)
    z = make_zone(book, direction=direction)
    z.state = ZoneState.READY
    z.imb_open = 95.0
    z.imb_body_top = 96.0
    z.imb_body_bot = 94.0
    h = BarHistory()
    for i in range(3):
        h.append(bar(i, 95, 97, 93, 95))
    z.state_bar_index = h.bar_index
    return sm, book, z, h


def test_skip_when_direction_disabled(cfg, ctx):
    cfg.tradeDirection = "Short only"
    sm, book, z, h = _ready_zone(cfg)
    sm.on_bar(h.current, h, ctx)
    assert z.state == ZoneState.INVALID
    assert any("SMER VYPNUTY" in e.reason for e in sm.events)


def test_skip_when_trading_disabled(cfg, ctx):
    cfg.enableTrading = False
    sm, book, z, h = _ready_zone(cfg)
    sm.on_bar(h.current, h, ctx)
    assert any("OBCHODOVANIE VYPNUTE" in e.reason for e in sm.events)


def test_skip_when_opposite_position_is_open(cfg):
    sm, book, z, h = _ready_zone(cfg)
    sm.on_bar(h.current, h, MarketContext(in_trade_window=True, position_size=-1))
    assert any("OPACNA POZICIA" in e.reason for e in sm.events)


def test_skip_when_daily_win_limit_reached(cfg):
    sm, book, z, h = _ready_zone(cfg)
    sm.on_bar(h.current, h, MarketContext(in_trade_window=True, daily_win_limit_reached=True))
    assert z.state == ZoneState.INVALID
    assert any("MAX DAILY" in e.reason for e in sm.events)


def test_skip_when_stop_is_too_tight(cfg, ctx):
    """Rozšírenie portu: `minSlDistance` v percentách ceny. Zóna z `_ready_zone` má
    vstup ~95 a SL zo swingu 93 mínus buffer, teda ~2 % — prah 5 % ju musí zahodiť,
    prah 1 % nie."""
    cfg.minSlDistance = {"value": 5.0, "unit": "pct"}
    sm, book, z, h = _ready_zone(cfg)
    intents = sm.on_bar(h.current, h, ctx)
    assert z.state == ZoneState.INVALID
    assert any("SL PRILIS TESNY" in e.reason for e in sm.events)
    assert intents == []


def test_min_sl_distance_off_by_default_and_passes_wide_stops(cfg, ctx):
    assert cfg.minSlDistance.value == 0.0
    cfg.minSlDistance = {"value": 1.0, "unit": "pct"}
    sm, book, z, h = _ready_zone(cfg)
    intents = sm.on_bar(h.current, h, ctx)
    assert z.state == ZoneState.ORDER_PENDING
    assert [i.action for i in intents] == [OrderAction.ENTRY]


def test_order_cancelled_outside_the_trade_window(cfg):
    sm, book, z, h = _ready_zone(cfg)
    intents = sm.on_bar(h.current, h, MarketContext(in_trade_window=False))
    assert z.state == ZoneState.INVALID
    assert [i.action for i in intents] == [OrderAction.CANCEL]


def test_structure_filter_blocks_when_bias_disagrees(cfg):
    cfg.useStructureFilter = True
    sm, book, z, h = _ready_zone(cfg)
    sm.on_bar(h.current, h, MarketContext(in_trade_window=True, market_bias=-1))
    assert any("STRUKTURA NESEDI" in e.reason for e in sm.events)


def test_structure_filter_allows_matching_bias(cfg):
    cfg.useStructureFilter = True
    sm, book, z, h = _ready_zone(cfg)
    intents = sm.on_bar(h.current, h, MarketContext(in_trade_window=True, market_bias=1))
    assert [i.action for i in intents] == [OrderAction.ENTRY]


def test_order_expires_after_state5_max_bars(cfg, ctx):
    cfg.state5MaxBars = 2
    sm, book, z, h = _ready_zone(cfg)
    sm.on_bar(h.current, h, ctx)  # zada order, prejde do STATE 5
    assert z.state == ZoneState.ORDER_PENDING

    intents = []
    for i in range(3, 8):
        h.append(bar(i, 95, 97, 93, 95))
        intents += sm.on_bar(h.current, h, ctx)

    assert z.state == ZoneState.INVALID
    cancels = [i for i in intents if i.action is OrderAction.CANCEL]
    assert [c.reason for c in cancels] == ["EXPIRED"]


def test_filled_order_survives_and_cancels_the_opposite_one(cfg, ctx):
    """OCO: kto vyplní prvý, vypína opačný čakajúci order."""
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    sm = StateMachine(cfg, MNQ, book)

    long_zone = make_zone(book, direction=Direction.LONG)
    short_zone = Zone(
        uid=1, direction=Direction.SHORT, top=100, bot=90,
        created_ms=T0, confirmed_ms=T0, expires_ms=T0 + 6 * 3_600_000,
    )
    book.zones.append(short_zone)

    for z in (long_zone, short_zone):
        z.state = ZoneState.ORDER_PENDING
        z.ordered = True
        z.imb_open = 95.0

    h = BarHistory()
    h.append(bar(0, 95, 97, 93, 95))
    for z in (long_zone, short_zone):
        z.state_bar_index = h.bar_index

    intents = sm.on_bar(
        h.current, h,
        MarketContext(in_trade_window=True, open_order_ids=frozenset({"LONG_0"})),
    )

    assert long_zone.filled is True
    assert short_zone.state == ZoneState.INVALID
    assert [(i.action, i.order_id) for i in intents] == [(OrderAction.CANCEL, "SHORT_1")]


def test_pattern_entry_jumps_straight_to_state4(ctx):
    """Pin Bar model ide z 0 rovno do 4 a SL si nesie z tej istej sviečky."""
    cfg = IBSConfig(enableImbEntry=False, enablePinBarEntry=True)
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    sm = StateMachine(cfg, MNQ, book)
    z = make_zone(book, top=100.0, bot=90.0)

    h = BarHistory()
    # Dotyk musi byt sviecka s VELKYM telom - dotyk aj pattern sa vyhodnocuju na tom
    # istom bare (rovnako ako v Pine), takze pin bar by tu inak vstupil uz on sam.
    h.append(bar(0, 99.5, 100, 91, 92))
    sm.on_bar(h.current, h, ctx)
    assert z.touched is True
    assert z.state == ZoneState.WAITING

    h.append(bar(1, 98.5, 99, 90.5, 99))  # pin bar vnutri zony
    intents = sm.on_bar(h.current, h, ctx)

    assert z.order_sl == pytest.approx(90.5 - 0.5)
    entries = [i for i in intents if i.action is OrderAction.ENTRY]
    assert len(entries) == 1
    assert entries[0].order_type is OrderType.MARKET  # pbEngOrderType default
    assert entries[0].plan.entry == 99.0  # vstup na zavreti sviecky


# --------------------------------------------------------------------------- #
# ATR — obsluhuje parametre v jednotke `atr` (rozšírenie portu, Pine ho nemá)
# --------------------------------------------------------------------------- #


def _atr_bar(i: int, high: float, low: float, close: float):
    from tradebot.core.types import Bar

    return Bar(time=i * 60_000, open=low, high=high, low=low, close=close, volume=1.0)


def test_atr_je_nula_kym_nie_je_dost_barov():
    from tradebot.core import BarHistory

    h = BarHistory(maxlen=50, atr_len=3)
    for i in range(2):
        h.append(_atr_bar(i, 110.0, 100.0, 105.0))
    assert h.atr == 0.0


def test_atr_prva_hodnota_je_priemer_true_range():
    from tradebot.core import BarHistory

    h = BarHistory(maxlen=50, atr_len=3)
    # prvý bar: TR = high-low = 10; ďalšie dva tiež 10 (žiadny gap)
    for i in range(3):
        h.append(_atr_bar(i, 110.0, 100.0, 105.0))
    assert h.atr == pytest.approx(10.0)


def test_atr_zapocita_gap_cez_predchadzajuci_close():
    from tradebot.core import BarHistory

    h = BarHistory(maxlen=50, atr_len=2)
    h.append(_atr_bar(0, 110.0, 100.0, 105.0))  # TR = 10
    h.append(_atr_bar(1, 130.0, 125.0, 128.0))  # gap hore: TR = 130 - 105 = 25
    assert h.atr == pytest.approx((10.0 + 25.0) / 2)


def test_atr_pokracuje_wilderovym_vyhladenim():
    from tradebot.core import BarHistory

    h = BarHistory(maxlen=50, atr_len=2)
    h.append(_atr_bar(0, 110.0, 100.0, 105.0))
    h.append(_atr_bar(1, 130.0, 125.0, 128.0))
    prev = h.atr
    h.append(_atr_bar(2, 130.0, 126.0, 128.0))  # TR = max(4, |130-128|, |126-128|) = 4
    assert h.atr == pytest.approx((prev * 1 + 4.0) / 2)


def test_engine_dopln_atr_ked_ho_volajuci_neposle():
    """Bez tohto boli všetky prahy v jednotke `atr` nulové — filtre vypnuté."""
    from tradebot.core import BarHistory, IBSConfig, IBSEngine
    from tradebot.core.types import BTCUSDT_BINANCE

    cfg = IBSConfig()
    cfg.atrLen = 3
    engine = IBSEngine(cfg, BTCUSDT_BINANCE, 3)
    for i in range(5):
        engine.on_bar(_atr_bar(i, 80_010.0, 80_000.0, 80_005.0))
    assert engine.history.atr == pytest.approx(10.0)
