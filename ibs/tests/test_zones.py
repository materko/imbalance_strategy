"""Testy detekcie SD zón a ich evidencie — replika Pine riadkov 274–279, 357–392, 638–660."""

from __future__ import annotations

import pytest

from ibs.core import (
    MNQ,
    Bar,
    Direction,
    HTFWindow,
    IBSConfig,
    SnapMode,
    Zone,
    ZoneBook,
    ZoneSource,
    detect_sd_pattern,
    snap_time,
)
from ibs.core.drawing import DrawKind, LineStyle
from ibs.core.zones import MAX_ZONES_HARD_CAP

FIVE_MIN = 300_000
THREE_MIN = 180_000
T0 = 1_756_684_800_000  # 2025-09-01 00:00:00 UTC, delitelne 3m aj 5m


def bar(t: int, o: float, h: float, low: float, c: float, v: float = 100.0) -> Bar:
    return Bar(time=t, open=o, high=h, low=low, close=c, volume=v)


def window(b3: Bar, b2: Bar, b1: Bar, b0: Bar, vol_sma: float = 100.0) -> HTFWindow:
    """Poradie argumentov je chronologické; HTFWindow ich drží od najnovšieho."""
    return HTFWindow(bars=(b0, b1, b2, b3), vol_sma=vol_sma)


def bull(t: int, base: float = 100.0, size: float = 2.0, vol: float = 100.0) -> Bar:
    return bar(t, base, base + size + 0.5, base - 0.5, base + size, vol)


def bear(t: int, base: float = 100.0, size: float = 2.0, vol: float = 100.0) -> Bar:
    return bar(t, base, base + 0.5, base - size - 0.5, base - size, vol)


@pytest.fixture
def cfg() -> IBSConfig:
    return IBSConfig()


# --------------------------------------------------------------------------- #
# snap_time
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "mode,expected",
    [
        (SnapMode.OFF, T0 + 100_000),
        (SnapMode.FLOOR, T0),
        (SnapMode.CEIL, T0 + THREE_MIN),
        (SnapMode.ROUND, T0 + THREE_MIN),
    ],
)
def test_snap_time_modes(mode, expected):
    assert snap_time(T0 + 100_000, THREE_MIN, mode) == expected


def test_snap_time_leaves_aligned_value_alone():
    for mode in SnapMode:
        assert snap_time(T0, THREE_MIN, mode) == T0


def test_snap_time_off_when_step_is_zero():
    assert snap_time(T0 + 7, 0, SnapMode.FLOOR) == T0 + 7


# --------------------------------------------------------------------------- #
# Detekcia patternu
# --------------------------------------------------------------------------- #


def test_long_v1_three_bulls_after_a_bear(cfg):
    """Pine longV1: bear[4], bull[3], bull[2], bull[1]."""
    w = window(
        bear(T0 + 0 * FIVE_MIN, 100),
        bull(T0 + 1 * FIVE_MIN, 100),
        bull(T0 + 2 * FIVE_MIN, 103),
        bull(T0 + 3 * FIVE_MIN, 106),
    )
    p = detect_sd_pattern(w, cfg, MNQ)
    assert p is not None
    assert p.direction is Direction.LONG
    assert p.variant == "longV1"


def test_short_v1_three_bears_after_a_bull(cfg):
    w = window(
        bull(T0 + 0 * FIVE_MIN, 100),
        bear(T0 + 1 * FIVE_MIN, 100),
        bear(T0 + 2 * FIVE_MIN, 97),
        bear(T0 + 3 * FIVE_MIN, 94),
    )
    p = detect_sd_pattern(w, cfg, MNQ)
    assert p is not None
    assert p.direction is Direction.SHORT
    assert p.variant == "shortV1"


def test_zone_bounds_come_from_the_oldest_bar(cfg):
    """Pine zTop5 = h5_3, zBot5 = l5_3 - rozsah základovej (najstaršej) sviečky."""
    base = bar(T0, 100, 111.0, 88.0, 98)  # bear, vyrazny rozsah
    w = window(base, bull(T0 + FIVE_MIN, 100), bull(T0 + 2 * FIVE_MIN, 103), bull(T0 + 3 * FIVE_MIN, 106))
    p = detect_sd_pattern(w, cfg, MNQ)
    assert (p.top, p.bot) == (111.0, 88.0)
    assert p.base_ms == T0
    assert p.confirm_ms == T0 + 3 * FIVE_MIN


def test_long_v2_uses_imbalance_between_bars_0_and_2(cfg):
    """bear, bull, cokolvek, a medzera medzi low[0] a high[2] >= minImbSizePoints (2.5)."""
    b3 = bear(T0, 100)
    b2 = bull(T0 + FIVE_MIN, 100)  # high = 102.5
    b1 = bar(T0 + 2 * FIVE_MIN, 104, 106, 103, 103.5)  # bearish, aby nesedel V1
    b0 = bar(T0 + 3 * FIVE_MIN, 106, 108, 105.5, 105.6)  # low 105.5 - 102.5 = 3.0 >= 2.5
    p = detect_sd_pattern(window(b3, b2, b1, b0), cfg, MNQ)
    assert p is not None
    assert p.variant == "longV2"


def test_imbalance_variants_rejected_when_gap_too_small(cfg):
    """Tvar bear+bull sedí, ale obe medzery sú pod minImbSizePoints (2.5) - a V1 nesedí."""
    b3 = bar(T0, 100, 102.0, 97.5, 98)  # bear, high 102.0
    b2 = bull(T0 + FIVE_MIN, 100)  # high 102.5
    b1 = bar(T0 + 2 * FIVE_MIN, 104, 106, 103.0, 103.5)  # bearish; V3 medzera 103.0-102.0 = 1.0
    b0 = bar(T0 + 3 * FIVE_MIN, 104, 105, 103.5, 103.6)  # V2 medzera 103.5-102.5 = 1.0
    assert detect_sd_pattern(window(b3, b2, b1, b0), cfg, MNQ) is None


def test_long_v3_uses_imbalance_between_bars_1_and_3(cfg):
    b3 = bar(T0, 100, 100.5, 97, 98)  # bear, high = 100.5
    b2 = bull(T0 + FIVE_MIN, 101)
    b1 = bar(T0 + 2 * FIVE_MIN, 105, 106, 104.0, 104.5)  # low 104 - 100.5 = 3.5 >= 2.5
    b0 = bar(T0 + 3 * FIVE_MIN, 104.5, 105, 104.2, 104.3)  # bearish, aby nesedel V1
    p = detect_sd_pattern(window(b3, b2, b1, b0), cfg, MNQ)
    assert p is not None
    assert p.variant == "longV3"


def test_no_pattern_when_shape_does_not_match(cfg):
    w = window(
        bull(T0, 100),
        bull(T0 + FIVE_MIN, 100),
        bull(T0 + 2 * FIVE_MIN, 103),
        bull(T0 + 3 * FIVE_MIN, 106),
    )
    assert detect_sd_pattern(w, cfg, MNQ) is None


def test_doji_is_neither_bull_nor_bear(cfg):
    """Pine isBull/isBear su ostre nerovnosti - close == open nie je ani jedno."""
    doji = bar(T0, 100, 101, 99, 100)
    w = window(doji, bull(T0 + FIVE_MIN, 100), bull(T0 + 2 * FIVE_MIN, 103), bull(T0 + 3 * FIVE_MIN, 106))
    assert detect_sd_pattern(w, cfg, MNQ) is None


# --------------------------------------------------------------------------- #
# Volume filter
# --------------------------------------------------------------------------- #


def _long_v1_window(vol: float, vol_sma: float) -> HTFWindow:
    return window(
        bear(T0, 100, vol=vol),
        bull(T0 + FIVE_MIN, 100, vol=vol),
        bull(T0 + 2 * FIVE_MIN, 103, vol=vol),
        bull(T0 + 3 * FIVE_MIN, 106, vol=vol),
        vol_sma=vol_sma,
    )


def test_volume_filter_off_by_default_leaves_zone_weak(cfg):
    p = detect_sd_pattern(_long_v1_window(vol=1000, vol_sma=100), cfg, MNQ)
    assert p is not None and p.volume_strong is False


def test_volume_filter_marks_strong_zone():
    cfg = IBSConfig(useVolumeFilter=True)  # volMultiplier default 1.5
    p = detect_sd_pattern(_long_v1_window(vol=200, vol_sma=100), cfg, MNQ)
    assert p is not None and p.volume_strong is True


def test_weak_zone_still_created_when_blocking_is_off():
    cfg = IBSConfig(useVolumeFilter=True, volumeFilterBlockTrading=False)
    p = detect_sd_pattern(_long_v1_window(vol=100, vol_sma=100), cfg, MNQ)
    assert p is not None and p.volume_strong is False


def test_weak_zone_blocked_when_both_switches_on():
    cfg = IBSConfig(useVolumeFilter=True, volumeFilterBlockTrading=True)
    assert detect_sd_pattern(_long_v1_window(vol=100, vol_sma=100), cfg, MNQ) is None


def test_strong_zone_passes_the_block():
    cfg = IBSConfig(useVolumeFilter=True, volumeFilterBlockTrading=True)
    p = detect_sd_pattern(_long_v1_window(vol=200, vol_sma=100), cfg, MNQ)
    assert p is not None and p.volume_strong is True


# --------------------------------------------------------------------------- #
# ZoneBook
# --------------------------------------------------------------------------- #


@pytest.fixture
def book(cfg) -> ZoneBook:
    return ZoneBook(cfg, MNQ, chart_tf_minutes=3)


def _pattern(book: ZoneBook, cfg: IBSConfig, base_ms: int):
    w = window(
        bear(base_ms, 100),
        bull(base_ms + FIVE_MIN, 100),
        bull(base_ms + 2 * FIVE_MIN, 103),
        bull(base_ms + 3 * FIVE_MIN, 106),
    )
    return detect_sd_pattern(w, cfg, MNQ)


def test_zone_created_with_snapped_bounds(book, cfg):
    p = _pattern(book, cfg, T0 + 100_000)  # nezarovnany cas
    z = book.create_from_pattern(p, now_ms=T0 + 100_000)
    assert z is not None
    assert z.created_ms == T0  # Floor na 3m grid
    assert z.expires_ms == T0 + cfg.zoneValidHours * 3_600_000
    assert z.source is ZoneSource.SD
    assert len(book) == 1


def test_same_base_candle_does_not_create_two_zones(book, cfg):
    p = _pattern(book, cfg, T0)
    assert book.create_from_pattern(p, now_ms=T0) is not None
    assert book.create_from_pattern(p, now_ms=T0) is None  # Pine lastDrawT0
    assert len(book) == 1


def test_next_base_candle_creates_another_zone(book, cfg):
    assert book.create_from_pattern(_pattern(book, cfg, T0), now_ms=T0) is not None
    assert book.create_from_pattern(_pattern(book, cfg, T0 + FIVE_MIN), now_ms=T0) is not None
    assert len(book) == 2
    assert [z.uid for z in book.zones] == [0, 1]


def test_zone_detection_switch_blocks_creation(cfg):
    cfg.enableZoneDetection = False
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    assert book.create_from_pattern(_pattern(book, cfg, T0), now_ms=T0) is None


def test_oldest_zone_is_evicted_over_the_limit(cfg):
    cfg.maxSdZones = 10
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    for i in range(15):
        book.create_from_pattern(_pattern(book, cfg, T0 + i * FIVE_MIN), now_ms=T0)
    assert len(book) == 10
    assert book.evicted == 5
    assert [z.uid for z in book.zones] == list(range(5, 15))


def test_hard_cap_of_200_applies(cfg):
    cfg.maxSdZones = 999
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    assert book.max_zones == MAX_ZONES_HARD_CAP


def test_confirm_time_is_clamped_into_the_zone_lifetime(book, cfg):
    p = _pattern(book, cfg, T0)
    z = book.create_from_pattern(p, now_ms=T0)
    assert z.created_ms <= z.confirmed_ms <= z.expires_ms


def test_expiry_and_cleanup(book, cfg):
    z = book.create_from_pattern(_pattern(book, cfg, T0), now_ms=T0)
    assert z.is_expired(z.expires_ms - 1) is False
    assert z.is_expired(z.expires_ms) is True
    assert book.active(z.expires_ms) == []
    assert book.drop_expired(z.expires_ms) == [z]
    assert len(book) == 0


def test_contains_and_height(book, cfg):
    z = book.create_from_pattern(_pattern(book, cfg, T0), now_ms=T0)
    mid = (z.top + z.bot) / 2
    assert z.contains(mid)
    assert not z.contains(z.top + 1)
    assert z.height == pytest.approx(z.top - z.bot)


# --------------------------------------------------------------------------- #
# Kreslenie
# --------------------------------------------------------------------------- #


def test_zone_draws_pre_and_post_box(book, cfg):
    z = book.create_from_pattern(_pattern(book, cfg, T0), now_ms=T0)
    pre, post = z.boxes(step_ms=THREE_MIN)

    assert pre.kind is DrawKind.SD_ZONE_PRE
    assert pre.border_style is LineStyle.DOTTED
    assert pre.fill_color is None

    assert post.kind is DrawKind.SD_ZONE_POST
    assert post.border_style is LineStyle.SOLID
    assert post.fill_color is not None

    assert pre.x1_ms == z.created_ms
    assert post.x1_ms == z.confirmed_ms
    assert post.x2_ms == z.expires_ms
    for b in (pre, post):
        assert (b.y1, b.y2) == (z.top, z.bot)
        assert b.zone_uid == z.uid


def test_long_zone_is_red_and_short_zone_is_blue(book, cfg):
    long_zone = book.create_from_pattern(_pattern(book, cfg, T0), now_ms=T0)
    assert long_zone.color == "#be3c46"

    short = Zone(
        uid=99, direction=Direction.SHORT, top=10, bot=9,
        created_ms=T0, confirmed_ms=T0, expires_ms=T0 + 1000,
    )
    assert short.color == "#3b82f6"


def test_strong_zone_is_emerald():
    z = Zone(
        uid=1, direction=Direction.LONG, top=10, bot=9,
        created_ms=T0, confirmed_ms=T0, expires_ms=T0 + 1000,
        volume_strong=True,
    )
    assert z.color == "#10b981"


def test_pre_box_is_at_least_one_bar_wide(book, cfg):
    """Ked confT == leftT, Pine roztiahne pre-box o jeden bar (leftT + stepMs)."""
    z = Zone(
        uid=1, direction=Direction.LONG, top=10, bot=9,
        created_ms=T0, confirmed_ms=T0, expires_ms=T0 + 3_600_000,
    )
    pre, _ = z.boxes(step_ms=THREE_MIN)
    assert pre.x2_ms == T0 + THREE_MIN
