"""Engine SIGMA BREAKOUT 1.0 — prepis Rust stratégie `SigmaBreakout` (`rq_sdk`) bar po bare.

Čas = otvorenie baru v New Yorku. RTH = 9:30 ≤ t < 16:00. Na každom uzavretom bare:

  1. **nový deň** (dátum NY) — vynulovať open RTH a VWAP (pozícia by tu už nemala byť; ak je, zavrieť),
  2. **16:00** — t ≥ 16:00 s pozíciou → zavrieť; mimo RTH nič ďalšie,
  3. **open RTH** — prvý bar RTH dňa,
  4. **pásmo** — referencia (open RTH alebo VWAP k predošlému baru) ± `bandMult` × sigma, kde sigma = priemer
     |zavretie − open RTH| v tej istej minúte (HH:MM) za posledných `nSigmaDays` dní; obchoduje sa až keď je
     história plná aspoň v jednej minúte (predloha: `trading_enabled` sa zapne raz a ostane),
  5. **vstup** — zavretie nad horným pásmom a pozícia ≤ 0 → (zavrieť short) long; pod dolným a ≥ 0 → short,
  6. **VWAP a história minúty** sa doplnia týmto barom až po rozhodnutí (bez pohľadu dopredu).
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawCommand, DrawLine
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ..rqport import TradeDraw, close_all, market_entry
from .config import SigmaConfig
from .drawing import SIGMA_BAND, SIGMA_ENTRY

__all__ = ["SigmaEngine"]

NY = ZoneInfo("America/New_York")
_FAR_STOP = 0.10
_REF = "#ffd700"
_UP = "#26a69a"
_DN = "#ef5350"


class SigmaEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: SigmaConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=2, atr_len=14)
        self.n = max(2, int(cfg.nSigmaDays))
        self.warmup = Warmup(self.chart_tf_minutes).add(f"sigma {self.n} dní", self.n * 3 // 2 + 2, 1440)
        self.required_history = self.warmup.chart_bars
        self.slots: dict[int, deque[float]] = {}
        self.day = None
        self.day_open: float | None = None
        self.pv = self.vol = 0.0
        self.vwap_prev: float | None = None
        self.enabled = False
        self.draw = TradeDraw(self.step_ms)

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, long: bool, up: float, dn: float) -> None:
        cfg = self.cfg
        pct = cfg.slPct / 100.0 if cfg.slPct > 0 else _FAR_STOP
        stop = bar.close * (1 - pct) if long else bar.close * (1 + pct)
        plan = market_entry(out, cfg, self.inst, bar, idx, "sigma", long, stop, None,
                            f"Sigma {'long' if long else 'short'}: pásmo {dn:g}–{up:g}")
        if plan:
            self.draw.start(out, bar, "sigma", plan.entry, plan.stop_loss, plan.take_profit, SIGMA_ENTRY,
                            "Sigma long" if long else "Sigma short", long, show_tp=False)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        t = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        hhmm = t.hour * 100 + t.minute
        self.draw.tick(out, bar, pos)

        # ---- 1. nový deň ---------------------------------------------------------- #
        if t.date() != self.day:
            if pos != 0.0 and cfg.useCloseAtEnd:
                close_all(out, ctx, idx, "zmena dňa")
                pos = 0.0
            self.day = t.date()
            self.day_open = None
            self.pv = self.vol = 0.0
            self.vwap_prev = None

        # ---- 2. 16:00 ------------------------------------------------------------ #
        if hhmm >= 1600 and pos != 0.0 and cfg.useCloseAtEnd:
            close_all(out, ctx, idx, "16:00 NY")
            pos = 0.0
        if not 930 <= hhmm < 1600:
            return out

        # ---- 3. open RTH --------------------------------------------------------- #
        if self.day_open is None:
            self.day_open = bar.open
        ref = (self.vwap_prev if self.vwap_prev is not None else self.day_open) if cfg.useVwap else self.day_open

        # ---- 4. pásmo ------------------------------------------------------------- #
        hist = self.slots.setdefault(hhmm, deque(maxlen=self.n))
        full = len(hist) == self.n
        sigma = sum(hist) / len(hist) if hist else 0.0
        up, dn = ref + cfg.bandMult * sigma, ref - cfg.bandMult * sigma
        if full:
            end = bar.time + self.step_ms
            for lvl, col, name in ((up, _UP, "u"), (dn, _DN, "d"), (ref, _REF, "r")):
                out.drawings.append(DrawLine(SIGMA_BAND, bar.time, lvl, end, lvl, col, width=1,
                                             obj_id=f"sigma.{name}.{bar.time}"))
            self.enabled = True

        # ---- 5. vstup ------------------------------------------------------------- #
        if self.enabled:
            if bar.close > up and pos <= 0.0:
                if pos < 0.0:
                    close_all(out, ctx, idx, "opačný prieraz")
                self._enter(out, bar, idx, True, up, dn)
            elif bar.close < dn and pos >= 0.0:
                if pos > 0.0:
                    close_all(out, ctx, idx, "opačný prieraz")
                self._enter(out, bar, idx, False, up, dn)

        # ---- 6. VWAP a história minúty --------------------------------------------- #
        tp = (bar.high + bar.low + bar.close) / 3.0
        self.pv += tp * bar.volume
        self.vol += bar.volume
        if self.vol > 0:
            self.vwap_prev = self.pv / self.vol
        hist.append(abs(bar.close - self.day_open))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
