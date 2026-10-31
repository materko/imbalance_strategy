"""Engine WILLIAMS %R LONG 1.0 — prepis Rust stratégie `WprLong` (`rq_sdk`, sama port Pine v6) bar po bare.

Na každom uzavretom bare (len long):

  1. %R(`wprLen`) ešte nie je → zapamätať high a nič,
  2. **čakanie na nový prepad** — v pozícii sa zapne; vypne sa, keď %R vystúpi aspoň na `entryLevel`,
  3. **vstup** — bez pozície, bez čakania, %R < `entryLevel`: long trhom, čakanie sa zapne,
  4. **výstup** — v pozícii: zavretie nad high predošlej sviečky (`exitMode` 0 / 2) alebo %R ≥ `exitLevel` (1 / 2).

Predloha stop nemá; plán nesie poistku `stopPct` (0 = 10 %) a cieľ 100 R.
"""

from __future__ import annotations

from collections import deque

from tradebot.core.drawing import DrawCommand
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ..rqport import TradeDraw, close_all, market_entry
from .config import WprConfig
from .drawing import WPR_ENTRY

__all__ = ["WprEngine"]

_FAR_STOP = 0.10


class WprEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: WprConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        n = max(1, int(cfg.wprLen))
        self.history = BarHistory(maxlen=2, atr_len=14)
        self.warmup = Warmup(self.chart_tf_minutes).add(f"%R {n}", n)
        self.required_history = n
        self.win: deque[Bar] = deque(maxlen=n)
        self.prev_high: float | None = None
        self.wait = False
        self.draw = TradeDraw(self.step_ms)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        self.draw.tick(out, bar, pos)
        self.win.append(bar)

        # ---- 1. %R -------------------------------------------------------------- #
        if len(self.win) < self.win.maxlen:
            self.prev_high = bar.high
            return out
        hh = max(b.high for b in self.win)
        ll = min(b.low for b in self.win)
        wpr = -100.0 * (hh - bar.close) / (hh - ll) if hh > ll else -50.0

        in_long = pos > 0
        # ---- 2. čakanie na nový prepad ------------------------------------------ #
        if in_long:
            self.wait = True
        if self.wait and wpr >= cfg.entryLevel:
            self.wait = False

        # ---- 3. vstup ------------------------------------------------------------ #
        if pos == 0.0 and not self.wait and wpr < cfg.entryLevel:
            pct = cfg.stopPct / 100.0 if cfg.stopPct > 0 else _FAR_STOP
            plan = market_entry(out, cfg, self.inst, bar, idx, "wpr", True, bar.close * (1 - pct), None,
                                f"%R long ({wpr:.1f})")
            self.wait = True
            if plan:
                self.draw.start(out, bar, "wpr", plan.entry, plan.stop_loss, plan.take_profit, WPR_ENTRY,
                                f"%R {wpr:.0f}", True, show_tp=False)

        # ---- 4. výstup ----------------------------------------------------------- #
        mode = int(cfg.exitMode)
        ex_prior = in_long and mode in (0, 2) and self.prev_high is not None and bar.close > self.prev_high
        ex_wpr = in_long and mode in (1, 2) and wpr >= cfg.exitLevel
        if ex_prior or ex_wpr:
            close_all(out, ctx, idx, "nad high predošlej sviečky" if ex_prior else f"%R {wpr:.0f}")
            self.wait = True
        self.prev_high = bar.high
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
