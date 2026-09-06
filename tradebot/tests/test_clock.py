"""Testy session okien — replika Pine `inWindowTZ` / `isWeekdayTZ` / `sessionHasTimeLeft`."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradebot.core import IBSConfig, SessionClock, SessionWindow, load_profile
from tradebot.core.clock import _pine_dayofweek


def ms(tz: str, y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> int:
    """Lokálny čas v pásme `tz` → ms epoch."""
    return int(datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(tz)).timestamp() * 1000)


NY = "America/New_York"
PRAGUE = "Europe/Prague"
LONDON = "Europe/London"


@pytest.fixture
def clock() -> SessionClock:
    """Nastavenia z grafu: sess2 NY zóna 08:00-11:00, trade 10:00-15:45."""
    cfg, _ = load_profile("golden_binance_btcusdt_3m")
    return SessionClock(cfg)


# --------------------------------------------------------------------------- #
# Základné okná
# --------------------------------------------------------------------------- #


def test_inside_trade_window(clock):
    st = clock.state(ms(NY, 2026, 9, 2, 14, 0))  # streda 14:00 NY
    assert st.trade_flags[1] is True
    assert st.in_trade_window


def test_before_trade_window(clock):
    st = clock.state(ms(NY, 2026, 9, 2, 9, 0))
    assert st.trade_flags[1] is False


def test_trade_window_end_is_exclusive(clock):
    """Pine `t2 >= st and t2 < en2` - koniec okna do neho už nepatrí."""
    assert clock.state(ms(NY, 2026, 9, 2, 15, 44)).trade_flags[1] is True
    assert clock.state(ms(NY, 2026, 9, 2, 15, 45)).trade_flags[1] is False


def test_zone_window_opens_before_trade_window(clock):
    """sess2ZoneStartH=8, sess2TradeStartH=10 - o 8:30 sa už kreslia zóny, ale neobchoduje."""
    st = clock.state(ms(NY, 2026, 9, 2, 8, 30))
    assert st.zone_flags[1] is True
    assert st.trade_flags[1] is False
    assert st.in_zone_window and not st.in_trade_window


def test_session3_london_window(clock):
    """sess3: Londýn, zóna 08:00-10:00, trade 08:00-11:00."""
    st = clock.state(ms(LONDON, 2026, 9, 2, 9, 0))
    assert st.zone_flags[2] is True
    assert st.trade_flags[2] is True
    st = clock.state(ms(LONDON, 2026, 9, 2, 10, 30))
    assert st.zone_flags[2] is False
    assert st.trade_flags[2] is True


def test_session1_disabled_in_profile(clock):
    """sess1On=False - Ázia je vypnutá, aj keď je vnútri jej času."""
    st = clock.state(ms(PRAGUE, 2026, 9, 2, 3, 0))
    assert st.zone_flags[0] is False
    assert st.trade_flags[0] is False


# --------------------------------------------------------------------------- #
# Dni v týždni
# --------------------------------------------------------------------------- #


def test_pine_dayofweek_mapping():
    """Pine: nedeľa=1 … sobota=7."""
    assert _pine_dayofweek(ms(NY, 2026, 9, 6), NY) == 1  # nedeľa
    assert _pine_dayofweek(ms(NY, 2026, 9, 7), NY) == 2  # pondelok
    assert _pine_dayofweek(ms(NY, 2026, 9, 11), NY) == 6  # piatok
    assert _pine_dayofweek(ms(NY, 2026, 9, 12), NY) == 7  # sobota


def test_weekend_is_blocked(clock):
    saturday = ms(NY, 2026, 9, 5, 14, 0)
    sunday = ms(NY, 2026, 9, 6, 14, 0)
    assert not clock.state(saturday).in_trade_window
    assert not clock.state(sunday).in_trade_window


def test_weekend_allowed_when_weekdays_only_off():
    cfg, _ = load_profile("golden_binance_btcusdt_3m")
    cfg.weekdaysOnly = False
    assert SessionClock(cfg).state(ms(NY, 2026, 9, 5, 14, 0)).in_trade_window


def test_weekday_is_evaluated_in_session_timezone():
    """Sobota 01:00 v Prahe je ešte piatok 19:00 v NY - a to rozhoduje."""
    cfg, _ = load_profile("golden_binance_btcusdt_3m")
    clock = SessionClock(cfg)
    ts = ms(PRAGUE, 2026, 9, 5, 1, 0)  # sobota v Prahe
    assert clock.is_weekday(ts, PRAGUE) is False
    assert clock.is_weekday(ts, NY) is True


# --------------------------------------------------------------------------- #
# Okná cez polnoc
# --------------------------------------------------------------------------- #


@pytest.fixture
def overnight_clock() -> SessionClock:
    cfg = IBSConfig(
        sess1On=True,
        sess1TZ=PRAGUE,
        sess1ZoneStartH=22, sess1ZoneStartM=0, sess1ZoneEndH=2, sess1ZoneEndM=0,
        sess1TradeStartH=22, sess1TradeStartM=0, sess1TradeEndH=2, sess1TradeEndM=0,
        weekdaysOnly=False,
    )
    return SessionClock(cfg)


@pytest.mark.parametrize(
    "hour,minute,expected",
    [(21, 59, False), (22, 0, True), (23, 30, True), (0, 30, True), (1, 59, True), (2, 0, False), (12, 0, False)],
)
def test_overnight_window(overnight_clock, hour, minute, expected):
    ts = ms(PRAGUE, 2026, 9, 2, hour, minute)
    assert overnight_clock.state(ts).trade_flags[0] is expected


# --------------------------------------------------------------------------- #
# Letný / zimný čas
# --------------------------------------------------------------------------- #


def test_window_follows_local_wall_clock_across_dst(clock):
    """14:00 v NY je vnútri okna v lete (EDT) aj v zime (EST) - hoci UTC sa líši."""
    summer = ms(NY, 2026, 7, 15, 14, 0)
    winter = ms(NY, 2026, 1, 15, 14, 0)
    assert clock.state(summer).trade_flags[1] is True
    assert clock.state(winter).trade_flags[1] is True

    summer_utc = datetime.fromtimestamp(summer / 1000, tz=ZoneInfo("UTC")).hour
    winter_utc = datetime.fromtimestamp(winter / 1000, tz=ZoneInfo("UTC")).hour
    assert summer_utc == 18  # EDT = UTC-4
    assert winter_utc == 19  # EST = UTC-5


def test_dst_shift_day_still_resolves(clock):
    """Deň prechodu na letný čas nesmie spôsobiť výnimku ani prázdne okno."""
    # 2026-03-08 je v USA prechod na EDT (02:00 -> 03:00).
    st = clock.state(ms(NY, 2026, 3, 9, 14, 0))
    assert st.trade_flags[1] is True


# --------------------------------------------------------------------------- #
# sessionHasTimeLeft / koniec dňa
# --------------------------------------------------------------------------- #


def test_sessions_have_time_left_during_the_day(clock):
    assert clock.state(ms(NY, 2026, 9, 2, 11, 0)).no_more_sessions_today is False


def test_no_more_sessions_after_last_window(clock):
    """Po 15:45 NY už žiadna zo zapnutých seáns dnes trade okno nemá."""
    assert clock.state(ms(NY, 2026, 9, 2, 16, 30)).no_more_sessions_today is True


def test_no_more_sessions_on_weekend(clock):
    assert clock.state(ms(NY, 2026, 9, 5, 12, 0)).no_more_sessions_today is True


# --------------------------------------------------------------------------- #
# Drobnosti
# --------------------------------------------------------------------------- #


def test_active_trade_session_index(clock):
    st = clock.state(ms(NY, 2026, 9, 2, 14, 0))
    assert st.active_trade_session() == 2
    # 20:00 NY = 01:00 nasledujuceho dna v Londyne - mimo vsetkych okien
    st = clock.state(ms(NY, 2026, 9, 2, 20, 0))
    assert st.active_trade_session() is None


def test_sessions_in_different_timezones_can_overlap(clock):
    """03:00 NY je 08:00 v Londýne - session 3 vtedy naozaj beží, hoci NY spí."""
    st = clock.state(ms(NY, 2026, 9, 2, 3, 0))
    assert st.trade_flags[1] is False
    assert st.trade_flags[2] is True
    assert st.active_trade_session() == 3


def test_session_window_str():
    assert str(SessionWindow(10, 0, 15, 45)) == "10:00-15:45"


def test_describe_is_readable(clock):
    line = clock.describe(ms(NY, 2026, 9, 2, 14, 0))
    assert "session2[-T]" in line
