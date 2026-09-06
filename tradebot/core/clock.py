"""Sessions a časové okná — presná replika Pine riadkov 283–322.

Každá z troch seáns má **dve nezávislé okná**:
  * *zone window*  — kedy sa smú vytvárať nové SD zóny
  * *trade window* — kedy sa smie poslať reálny order

Nemusia sa prekrývať a každá seansa má vlastné časové pásmo.

Dôležitý detail, ktorý sa ľahko prehliadne: Pine počíta hranice okna z **dátumu
aktuálneho baru v danom časovom pásme**, nie z UTC. Vďaka tomu okno „sedí" na
lokálnom čase burzy aj cez prechody na letný/zimný čas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from .config import IBSConfig
from .drawing import DrawBg, DrawKind, Palette, with_alpha

__all__ = ["SessionWindow", "SessionSpec", "ClockState", "SessionClock", "DAY_MS"]

DAY_MS = 86_400_000

#: Pine `dayofweek`: nedeľa=1 … sobota=7. Python `weekday()`: pondelok=0 … nedeľa=6.
_PINE_MONDAY = 2
_PINE_FRIDAY = 6


@lru_cache(maxsize=32)
def _zone(tz: str) -> ZoneInfo:
    return ZoneInfo(tz)


def _local(ts_ms: int, tz: str) -> datetime:
    return datetime.fromtimestamp(ts_ms / 1000, tz=_zone(tz))


def _timestamp_ms(tz: str, year: int, month: int, day: int, hour: int, minute: int) -> int:
    """Pine `timestamp(tz, y, mo, d, h, m)` — lokálny čas v danom pásme → ms epoch."""
    dt = datetime(year, month, day, hour, minute, tzinfo=_zone(tz))
    return int(dt.timestamp() * 1000)


def _pine_dayofweek(ts_ms: int, tz: str) -> int:
    return (_local(ts_ms, tz).weekday() + 1) % 7 + 1


@dataclass(frozen=True, slots=True)
class SessionWindow:
    start_h: int
    start_m: int
    end_h: int
    end_m: int

    def __str__(self) -> str:
        return f"{self.start_h:02d}:{self.start_m:02d}-{self.end_h:02d}:{self.end_m:02d}"


@dataclass(frozen=True, slots=True)
class SessionSpec:
    name: str
    enabled: bool
    tz: str
    zone: SessionWindow
    trade: SessionWindow


@dataclass(frozen=True, slots=True)
class ClockState:
    """Stav času pre jeden bar."""

    zone_flags: tuple[bool, bool, bool]  # s1Zone, s2Zone, s3Zone
    trade_flags: tuple[bool, bool, bool]  # s1Trade, s2Trade, s3Trade
    no_more_sessions_today: bool

    @property
    def in_zone_window(self) -> bool:
        return any(self.zone_flags)

    @property
    def in_trade_window(self) -> bool:
        return any(self.trade_flags)

    def backgrounds(self, ts_ms: int, step_ms: int) -> list[DrawBg]:
        """Pine `bgcolor()` na riadkoch 331–333 — pás pozadia pre tento bar.

        Priehľadnosť je 92 v trade okne a 96 v zone okne; trade okno má prednosť,
        lebo v Pine je to ternárny výraz, nie dva prekryté `bgcolor` hovory.
        Jeden bar = jeden pás; susedné pásy si zlúči až renderer.
        """
        out: list[DrawBg] = []
        for i, (zone, trade) in enumerate(zip(self.zone_flags, self.trade_flags), start=1):
            if not (zone or trade):
                continue
            base = getattr(Palette, f"SESSION{i}").value
            out.append(
                DrawBg(
                    kind=DrawKind.SESSION,
                    x1_ms=ts_ms,
                    x2_ms=ts_ms + step_ms,
                    color=with_alpha(base, 92 if trade else 96),
                    obj_id=f"bg{i}.{ts_ms}",
                    text=f"Session {i}",
                )
            )
        return out

    def active_trade_session(self) -> int | None:
        """1-based index prvej seansy, ktorá práve dovoľuje obchodovať."""
        for i, flag in enumerate(self.trade_flags, start=1):
            if flag:
                return i
        return None


class SessionClock:
    """Vyhodnocuje session okná pre daný čas baru.

    Bezstavové — všetko sa počíta z `ts_ms`, takže sa dá volať aj mimo poradia
    (napr. pri vektorizovanom predpočítaní vo Freqtrade adaptéri).
    """

    def __init__(self, cfg: IBSConfig) -> None:
        self.weekdays_only = cfg.weekdaysOnly
        self.sessions: tuple[SessionSpec, ...] = tuple(
            SessionSpec(
                name=f"session{n}",
                enabled=getattr(cfg, f"sess{n}On"),
                tz=getattr(cfg, f"sess{n}TZ"),
                zone=SessionWindow(
                    getattr(cfg, f"sess{n}ZoneStartH"),
                    getattr(cfg, f"sess{n}ZoneStartM"),
                    getattr(cfg, f"sess{n}ZoneEndH"),
                    getattr(cfg, f"sess{n}ZoneEndM"),
                ),
                trade=SessionWindow(
                    getattr(cfg, f"sess{n}TradeStartH"),
                    getattr(cfg, f"sess{n}TradeStartM"),
                    getattr(cfg, f"sess{n}TradeEndH"),
                    getattr(cfg, f"sess{n}TradeEndM"),
                ),
            )
            for n in (1, 2, 3)
        )

    # -- Pine helpers ---------------------------------------------------- #

    def is_weekday(self, ts_ms: int, tz: str) -> bool:
        """Pine `isWeekdayTZ` — deň v týždni sa berie v pásme danej seansy, nie v UTC."""
        if not self.weekdays_only:
            return True
        return _PINE_MONDAY <= _pine_dayofweek(ts_ms, tz) <= _PINE_FRIDAY

    def in_window(self, ts_ms: int, w: SessionWindow, tz: str) -> bool:
        """Pine `inWindowTZ` — vrátane posunu o deň, ktorý rieši okná cez polnoc."""
        local = _local(ts_ms, tz)
        start = _timestamp_ms(tz, local.year, local.month, local.day, w.start_h, w.start_m)
        end = _timestamp_ms(tz, local.year, local.month, local.day, w.end_h, w.end_m)

        end2 = end + DAY_MS if end <= start else end
        t2 = ts_ms + DAY_MS if ts_ms < start else ts_ms
        return start <= t2 < end2

    def session_has_time_left(self, ts_ms: int, s: SessionSpec) -> bool:
        """Pine `sessionHasTimeLeft` — má ešte dnes trade okno tejto seansy dobehnúť?"""
        if not s.enabled or not self.is_weekday(ts_ms, s.tz):
            return False
        local = _local(ts_ms, s.tz)
        start = _timestamp_ms(
            s.tz, local.year, local.month, local.day, s.trade.start_h, s.trade.start_m
        )
        end = _timestamp_ms(s.tz, local.year, local.month, local.day, s.trade.end_h, s.trade.end_m)
        if end <= start:
            end += DAY_MS
        return ts_ms < end

    # -- verejné API ------------------------------------------------------ #

    def state(self, ts_ms: int) -> ClockState:
        zone_flags = []
        trade_flags = []
        has_time = []
        for s in self.sessions:
            weekday_ok = s.enabled and self.is_weekday(ts_ms, s.tz)
            zone_flags.append(weekday_ok and self.in_window(ts_ms, s.zone, s.tz))
            trade_flags.append(weekday_ok and self.in_window(ts_ms, s.trade, s.tz))
            has_time.append(self.session_has_time_left(ts_ms, s))

        return ClockState(
            zone_flags=tuple(zone_flags),
            trade_flags=tuple(trade_flags),
            no_more_sessions_today=not any(has_time),
        )

    def describe(self, ts_ms: int) -> str:
        """Jednoriadkový popis pre logy a ladenie."""
        st = self.state(ts_ms)
        parts = []
        for i, s in enumerate(self.sessions):
            marks = ("Z" if st.zone_flags[i] else "-") + ("T" if st.trade_flags[i] else "-")
            parts.append(f"{s.name}[{marks}]")
        utc = datetime.fromtimestamp(ts_ms / 1000, tz=ZoneInfo("UTC"))
        return f"{utc:%Y-%m-%d %H:%M} UTC  " + " ".join(parts)
