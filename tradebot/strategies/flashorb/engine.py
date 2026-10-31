"""Engine FLASH TRIGGER ORB 1.0 — prepis Rust stratégie `FlashTriggerOrb` (`rq_sdk`) bar po bare.

Miestny čas = UTC + `utcOffset` (pevne, bez letného času — ako predloha). Na každom uzavretom bare:

  1. **nový miestny deň** — zrušiť range a obchod dňa,
  2. **koniec dňa UTC** — raz za deň UTC od `eodHour`:`eodMinute` zavrieť pozíciu (vstupy neblokuje),
  3. **range** — bar s miestnym časom otvorenia `targetHour`:`targetMinute` (filter dní) dá high / low a nič ďalšie,
  4. **vstup** — od ďalšieho baru, bez pozície, ešte bez obchodu na range: zavretie nad high long (stop low),
     pod low short (stop high), cieľ `riskReward` × stop, voliteľný trailing v bodoch.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tradebot.core.drawing import DrawBox, DrawCommand, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.risk import TrailingPlan
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ..rqport import TradeDraw, close_all, market_entry
from .config import FlashorbConfig
from .drawing import FLASHORB_ENTRY, FLASHORB_ZONE

__all__ = ["FlashorbEngine"]

_ZONE = "#00c853"


class FlashorbEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: FlashorbConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=2, atr_len=14)
        self.warmup = Warmup(self.chart_tf_minutes)
        self.required_history = 1
        self.local_day = None
        self.utc_day = None
        self.closed_for_day = False
        self.active = False
        self.traded = False
        self.hi = self.lo = 0.0
        self.range_idx = -1
        self.draw = TradeDraw(self.step_ms)

    def _day_ok(self, local: datetime) -> bool:
        cfg = self.cfg
        if not cfg.dayFilter:
            return True
        return {1: cfg.tradeMonday, 2: cfg.tradeTuesday, 3: cfg.tradeWednesday, 4: cfg.tradeThursday,
                5: cfg.tradeFriday}.get(local.isoweekday(), False)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        utc = datetime.fromtimestamp(bar.time / 1000, tz=timezone.utc)
        local = utc + timedelta(hours=int(cfg.utcOffset))
        self.draw.tick(out, bar, pos)

        # ---- 1. nový miestny deň ----------------------------------------------- #
        if local.date() != self.local_day:
            self.local_day = local.date()
            self.active = False
            self.traded = False
        if utc.date() != self.utc_day:
            self.utc_day = utc.date()
            self.closed_for_day = False

        # ---- 2. koniec dňa UTC --------------------------------------------------- #
        if cfg.useEodClose and not self.closed_for_day and utc.hour * 100 + utc.minute >= int(cfg.eodHour) * 100 + int(cfg.eodMinute):
            if pos != 0.0:
                close_all(out, ctx, idx, "koniec dňa (UTC)")
                pos = 0.0
            self.closed_for_day = True

        # ---- 3. range ------------------------------------------------------------ #
        if (not self.active and local.hour == int(cfg.targetHour) and local.minute == int(cfg.targetMinute)
                and self._day_ok(local)):
            self.hi, self.lo = bar.high, bar.low
            self.active, self.traded, self.range_idx = True, False, idx
            out.drawings.append(DrawBox(FLASHORB_ZONE, bar.time, self.hi, bar.time + 6 * self.step_ms, self.lo, _ZONE,
                                        fill_color=with_alpha(_ZONE, 30), obj_id=f"flash.z.{bar.time}", text="Flash"))
            return out

        # ---- 4. vstup ------------------------------------------------------------- #
        if not self.active or self.traded or idx <= self.range_idx or pos != 0.0:
            return out
        long = bar.close > self.hi
        if not long and not bar.close < self.lo:
            return out
        stop = self.lo if long else self.hi
        dist = abs(bar.close - stop)
        take = bar.close + dist * cfg.riskReward if long else bar.close - dist * cfg.riskReward
        trail = None
        if cfg.activateTrailing:
            tick = self.inst.tick_size
            trail = TrailingPlan(cfg.trailActivatePoints, cfg.trailBufferPoints,
                                 cfg.trailActivatePoints / tick, cfg.trailBufferPoints / tick)
        plan = market_entry(out, cfg, self.inst, bar, idx, "flash", long, stop, take,
                            f"Flash ORB {'long' if long else 'short'}: {self.lo:g}–{self.hi:g}", trailing=trail)
        if plan:
            self.traded = True
            self.draw.start(out, bar, "flash", plan.entry, plan.stop_loss, plan.take_profit, FLASHORB_ENTRY,
                            "Flash long" if long else "Flash short", long)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
