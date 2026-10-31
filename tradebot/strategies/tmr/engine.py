"""Engine T-MEAN REVERSION 1.0 — prepis Rust stratégie `TMeanReversion` (`rq_sdk`) bar po bare.

Čas = otvorenie baru v UTC (predloha `bar.time`), deň 1 = pondelok … 7 = nedeľa. Na každom bare:

  1. **denná sviečka** — pri zmene kalendárneho dňa UTC: keď skončil piatok, červený = zavretie posledného baru
     piatku < otvorenie prvého baru piatku,
  2. **hodiny trhu** — pri `checkMarketHours` mimo [`marketOpenHour`, `marketCloseHour`) bar nič nerobí,
  3. **vstup** — deň `entryDay`, hodina `entryHour`, minúta ≥ `entryMinute`, raz za deň, bez pozície,
     po červenom piatku: long trhom na zavretí baru,
  4. **výstup** — deň `exitDay`, hodina `exitHour`, minúta ≥ `exitMinute`, raz za deň, s pozíciou: zavrieť.

Predloha stop ani cieľ nemá; plán nesie poistku `stopPct` (0 = 10 %) a cieľ 100 R.
"""

from __future__ import annotations

from datetime import datetime, timezone

from tradebot.core.drawing import DrawCommand
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ..rqport import TradeDraw, close_all, market_entry
from .config import TmrConfig
from .drawing import TMR_ENTRY

__all__ = ["TmrEngine"]

_FAR_STOP = 0.10


class TmrEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: TmrConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=2, atr_len=14)
        self.warmup = Warmup(self.chart_tf_minutes)
        self.required_history = 1
        self.cur_day = None
        self.cur_open = 0.0
        self.cur_wd = 0
        self.prev_close = 0.0
        self.friday_red = False
        self.have_friday = False
        self.last_entry = None
        self.last_exit = None
        self.draw = TradeDraw(self.step_ms)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        t = datetime.fromtimestamp(bar.time / 1000, tz=timezone.utc)
        wd = t.isoweekday()
        self.draw.tick(out, bar, pos)

        # ---- 1. denná sviečka ------------------------------------------------- #
        if self.cur_day is None:
            self.cur_day, self.cur_open, self.cur_wd = t.date(), bar.open, wd
        elif t.date() != self.cur_day:
            if self.cur_wd == 5:
                self.friday_red = self.prev_close < self.cur_open
                self.have_friday = True
            self.cur_day, self.cur_open, self.cur_wd = t.date(), bar.open, wd
        self.prev_close = bar.close

        # ---- 2. hodiny trhu ----------------------------------------------------- #
        if cfg.checkMarketHours and not (int(cfg.marketOpenHour) <= t.hour < int(cfg.marketCloseHour)):
            return out

        # ---- 3. vstup ----------------------------------------------------------- #
        if wd == int(cfg.entryDay) and t.hour == int(cfg.entryHour) and t.minute >= int(cfg.entryMinute):
            if t.date() != self.last_entry and pos == 0.0:
                self.last_entry = t.date()
                if not cfg.requireRedFriday or (self.have_friday and self.friday_red):
                    pct = cfg.stopPct / 100.0 if cfg.stopPct > 0 else _FAR_STOP
                    plan = market_entry(out, cfg, self.inst, bar, idx, "tmr", True, bar.close * (1 - pct), None,
                                        "T-MR long po červenom piatku")
                    if plan:
                        self.draw.start(out, bar, "tmr", plan.entry, plan.stop_loss, plan.take_profit, TMR_ENTRY,
                                        "T-MR", True, show_tp=False)

        # ---- 4. výstup ---------------------------------------------------------- #
        if wd == int(cfg.exitDay) and t.hour == int(cfg.exitHour) and t.minute >= int(cfg.exitMinute):
            if t.date() != self.last_exit and ctx.position_size != 0.0:
                self.last_exit = t.date()
                close_all(out, ctx, idx, "výstup v čase (streda)")
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
