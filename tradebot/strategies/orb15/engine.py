"""Engine ORB 15/5 1.0 — prepis Rust stratégie `Orb15m5mBreakout` (`rq_sdk`) bar po bare.

Poradie krokov na každom uzavretom bare (čas = otvorenie baru v New Yorku) je to isté ako v predlohe:

  1. **nový deň** (dátum NY) — vynulovať OR, bias a počítadlo obchodov,
  2. **OR** — bary `orStart` ≤ t < koniec OR rozšíria high / low a nič ďalšie,
  3. OR ešte nie je hotový → nič,
  4. **bias** — prvý bar od `biasCheck`: high / low predošlého obchodného dňa (CME, od 18:00 NY) voči zavretiu,
  5. **koniec** — t ≥ `lastEntry`: pri `closeAtEnd` zavrieť pozíciu, nový vstup nie,
  6. **vstup** — bez pozície, pod limitom obchodov: zavretie za OR (filter knôtu, bias), stop na druhej strane OR.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawUpdate, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import Orb15Config
from .drawing import ORB15_ENTRY, ORB15_ZONE

__all__ = ["Orb15Engine"]

NY = ZoneInfo("America/New_York")
_LONG = "#22c55e"
_SHORT = "#ef4444"
_ZONE = "#2196f3"


def _hm(v: int) -> int:
    return (int(v) // 100) * 60 + int(v) % 100


class Orb15Engine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: Orb15Config, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=4, atr_len=14)
        self.warmup = Warmup(self.chart_tf_minutes)
        self.required_history = 1
        self.day = None
        self.or_high = float("-inf")
        self.or_low = float("inf")
        self.or_ready = False
        self.or_start_ms = 0
        self.trades = 0
        self.bias_done = False
        self.longs_blocked = self.shorts_blocked = False
        # high / low obchodného dňa CME (18:00 NY → 17:00 NY): rozpracovaný a predošlý hotový
        self.tday = None
        self.tday_hl: tuple[float, float] | None = None
        self.prev_hl: tuple[float, float] | None = None
        self.boxes: list[str] = []
        self.was_in = False

    # ------------------------------------------------------------------ #

    def _close(self, out: EngineOutput, ctx: MarketContext, idx: int, reason: str) -> None:
        out.close_session = True
        for order_id in ctx.open_order_ids:
            out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason=reason))

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, long: bool) -> None:
        cfg, inst = self.cfg, self.inst
        entry = bar.close
        stop = self.or_low if long else self.or_high
        risk = abs(entry - stop)
        if risk < inst.tick_size:
            return
        dist = cfg.targetPoints if int(cfg.targetMode) == 1 else risk * cfg.rr
        take = inst.round_price(entry + dist if long else entry - dist)
        qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, risk)
        if qty <= 0:
            return
        plan = TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=entry, stop_loss=stop,
                         take_profit=take, qty=qty, sl_distance=risk)
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"orb15:{idx}", idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.MARKET,
                                      reason=f"ORB 15/5 {'long' if long else 'short'}: OR {self.or_low:g}–{self.or_high:g}"))
        self.trades += 1
        end = bar.time + self.step_ms
        self.boxes, self.was_in = [], False
        for kind, level, color in ((DrawKind.TP_BOX, take, _LONG), (DrawKind.SL_BOX, stop, _SHORT)):
            bid = f"orb15.{kind[:2]}.{bar.time}"
            out.drawings.append(DrawBox(kind, bar.time, max(entry, level), end, min(entry, level), color,
                                        fill_color=with_alpha(color, 60), obj_id=bid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(bid)
        out.drawings.append(DrawLabel(ORB15_ENTRY, bar.time, entry, "ORB long" if long else "ORB short", "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"orb15.e.{bar.time}"))

    def _track_day(self, bar: Bar, t: datetime) -> None:
        tday = (t + timedelta(hours=6)).date()          # 18:00 NY = začiatok ďalšieho obchodného dňa
        if tday != self.tday:
            if self.tday_hl is not None:
                self.prev_hl = self.tday_hl
            self.tday, self.tday_hl = tday, (bar.high, bar.low)
        else:
            h, lo = self.tday_hl
            self.tday_hl = (max(h, bar.high), min(lo, bar.low))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        t = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        mins = t.hour * 60 + t.minute
        prev_hl = self.prev_hl                           # hotový deň pred týmto barom
        self._track_day(bar, t)

        if self.boxes:
            for oid in self.boxes:
                out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
            if pos != 0.0:
                self.was_in = True
            elif self.was_in:
                self.boxes, self.was_in = [], False

        # ---- 1. nový deň ------------------------------------------------------ #
        if t.date() != self.day:
            self.day = t.date()
            self.or_high, self.or_low = float("-inf"), float("inf")
            self.or_ready = False
            self.trades = 0
            self.bias_done = False
            self.longs_blocked = self.shorts_blocked = False

        or_start = _hm(cfg.orStart)
        or_end = or_start + int(cfg.orMinutes)

        # ---- 2. OR ---------------------------------------------------------------- #
        if not self.or_ready and or_start <= mins < or_end:
            if self.or_high == float("-inf"):
                self.or_start_ms = bar.time
            self.or_high = max(self.or_high, bar.high)
            self.or_low = min(self.or_low, bar.low)
            if cfg.drawRange:
                out.drawings.append(DrawBox(ORB15_ZONE, self.or_start_ms, self.or_high,
                                            self.or_start_ms + int(cfg.orMinutes) * 60_000, self.or_low, _ZONE,
                                            fill_color=with_alpha(_ZONE, 38), obj_id=f"orb15.z.{self.or_start_ms}",
                                            text="OR"))
            return out

        # ---- 3. OR hotový? ---------------------------------------------------------- #
        if not self.or_ready and mins >= or_end and self.or_high != float("-inf"):
            self.or_ready = True
        if not self.or_ready:
            return out

        # ---- 4. bias predošlého dňa ------------------------------------------------- #
        if cfg.useDailyBias and not self.bias_done and mins >= _hm(cfg.biasCheck):
            self.bias_done = True
            if prev_hl is None:
                return out                               # predloha: bez dennej hodnoty koniec baru
            self.longs_blocked = bar.close < prev_hl[1]
            self.shorts_blocked = bar.close > prev_hl[0]

        # ---- 5. koniec -------------------------------------------------------------- #
        if t.hour * 100 + t.minute >= int(cfg.lastEntry):
            if cfg.closeAtEnd and pos != 0.0:
                self._close(out, ctx, idx, f"koniec {int(cfg.lastEntry):04d} NY")
            return out
        if pos != 0.0 or self.trades >= int(cfg.maxTradesPerDay):
            return out

        # ---- 6. vstup ---------------------------------------------------------------- #
        rng = bar.high - bar.low
        upper_wick = bar.high - max(bar.open, bar.close)
        lower_wick = min(bar.open, bar.close) - bar.low
        long_wick_bad = cfg.useWickFilter and rng > 0 and lower_wick / rng * 100.0 > cfg.maxWickPct
        short_wick_bad = cfg.useWickFilter and rng > 0 and upper_wick / rng * 100.0 > cfg.maxWickPct
        if cfg.allowLong and bar.close > self.or_high and not long_wick_bad and not self.longs_blocked:
            self._enter(out, bar, idx, True)
        elif cfg.allowShort and bar.close < self.or_low and not short_wick_bad and not self.shorts_blocked:
            self._enter(out, bar, idx, False)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
