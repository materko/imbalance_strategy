"""Engine NQ PRECISION 1.0 — prepis Rust stratégie `NqPrecisionBot` (`rq_sdk`) na sviečkach.

Predloha robí OR a filtre na zavretých 1m baroch (`on_bar`) a vstup / výstup na tickoch (`on_tick`). Port je na
zavretých baroch: cena ticku = zavretie baru, čas ticku = koniec baru (otvorenie + TF). Čas New York.

  1. **nový deň** — vynulovať OR, obchod dňa a okno objemu (predloha `reset_daily`),
  2. **vstup** (pred aktualizáciou filtrov — predloha ich číta z predošlého baru): bez pozície, OR hotový, dnes
     ešte nič; pri `useTriggerTime` prvý bar s koncom ≥ `triggerTime` — zavretie nad OR long, pod OR short, vnútri
     = deň skončil; bez snímky bary s koncom v [`rangeEnd`, `tradeUntil`] — prvý prieraz; filtre RVOL a režim ATR
     v pásmach (pri snímke nesplnené = deň skončil); stop / cieľ `atrSlMult` / `atrTpMult` × ATR,
  3. **výstup v čase** — pozícia otvorená aspoň `closeAfterMin` minút → zavrieť,
  4. **OR** — bary s otvorením `rangeStart` ≤ t < `rangeEnd`; hotový od prvého baru s otvorením ≥ `rangeEnd`,
  5. **filtre** — ATR / dlhé ATR a RVOL = objem baru / priemer posledných `rvolLen` objemov dňa (keď je okno plné).
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ..rqport import TradeDraw, close_all, market_entry
from .config import NqprecConfig
from .drawing import NQPREC_ENTRY, NQPREC_ZONE

__all__ = ["NqprecEngine"]

NY = ZoneInfo("America/New_York")
_ZONE = "#00c853"


class _Wilder:
    """ATR (Wilder RMA, seed SMA) — predloha `Atr::new(n)`."""

    def __init__(self, n: int) -> None:
        self.n, self.k, self.sum, self.val, self.prev_close = n, 0, 0.0, None, None

    def update(self, bar: Bar) -> float | None:
        tr = bar.high - bar.low if self.prev_close is None else max(
            bar.high - bar.low, abs(bar.high - self.prev_close), abs(bar.low - self.prev_close))
        self.prev_close = bar.close
        if self.val is None:
            self.k += 1
            self.sum += tr
            if self.k == self.n:
                self.val = self.sum / self.n
        else:
            self.val = (self.val * (self.n - 1) + tr) / self.n
        return self.val


class NqprecEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: NqprecConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=2, atr_len=14)
        self.atr = _Wilder(max(2, int(cfg.atrPeriod)))
        self.atr_long = _Wilder(max(2, int(cfg.atrRegimeLen)))
        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrRegimeLen}", max(2, int(cfg.atrRegimeLen)))
        self.required_history = max(2, int(cfg.atrRegimeLen))
        self.vols: deque[float] = deque(maxlen=max(2, int(cfg.rvolLen)))
        self.day = None
        self.have = self.locked = self.traded = False
        self.hi = self.lo = 0.0
        self.or_start_ms = 0
        self.atr_val: float | None = None
        self.regime = float("nan")
        self.rvol = float("nan")
        self.entry_ms: int | None = None
        self.draw = TradeDraw(self.step_ms)

    def _filters(self) -> bool:
        cfg = self.cfg
        if not cfg.useFilters:
            return True
        r, g = self.rvol, self.regime
        return (r == r and cfg.rvolMin <= r <= cfg.rvolMax) and (g == g and cfg.regimeMin <= g <= cfg.regimeMax)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        t = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        e = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
        open_hm, end_hm = t.hour * 100 + t.minute, e.hour * 100 + e.minute
        self.draw.tick(out, bar, pos)
        if pos == 0.0:
            self.entry_ms = None

        # ---- 1. nový deň ------------------------------------------------------------ #
        if t.date() != self.day:
            self.day = t.date()
            self.have = self.locked = self.traded = False
            self.regime = self.rvol = float("nan")
            self.vols.clear()

        # ---- 2. vstup --------------------------------------------------------------- #
        if pos == 0.0 and self.locked and not self.traded:
            if cfg.useTriggerTime:
                window = end_hm >= int(cfg.triggerTime)
            else:
                window = int(cfg.rangeEnd) <= end_hm <= int(cfg.tradeUntil)
            if window:
                px = bar.close
                d = 1 if px > self.hi else -1 if px < self.lo else 0
                if d == 0:
                    if cfg.useTriggerTime:
                        self.traded = True
                elif not self._filters():
                    if cfg.useTriggerTime:
                        self.traded = True
                elif self.atr_val:
                    self.traded = True
                    sl, tp = self.atr_val * cfg.atrSlMult, self.atr_val * cfg.atrTpMult
                    long = d > 0
                    plan = market_entry(out, cfg, self.inst, bar, idx, "nqp", long, px - sl if long else px + sl,
                                        px + tp if long else px - tp,
                                        f"NQ Precision {'long' if long else 'short'}: OR {self.lo:g}–{self.hi:g}")
                    if plan:
                        self.entry_ms = bar.time + self.step_ms
                        self.draw.start(out, bar, "nqp", plan.entry, plan.stop_loss, plan.take_profit, NQPREC_ENTRY,
                                        "NQP long" if long else "NQP short", long)
                elif cfg.useTriggerTime:
                    self.traded = True

        # ---- 3. výstup v čase ---------------------------------------------------------- #
        elif pos != 0.0 and cfg.useTimeClose and self.entry_ms is not None:
            if (bar.time + self.step_ms - self.entry_ms) >= int(cfg.closeAfterMin) * 60_000:
                close_all(out, ctx, idx, f"po {int(cfg.closeAfterMin)} min")
                self.entry_ms = None

        # ---- 4. OR ------------------------------------------------------------------- #
        if int(cfg.rangeStart) <= open_hm < int(cfg.rangeEnd):
            if not self.have:
                self.hi, self.lo, self.have, self.or_start_ms = bar.high, bar.low, True, bar.time
            else:
                self.hi, self.lo = max(self.hi, bar.high), min(self.lo, bar.low)
        if not self.locked and open_hm >= int(cfg.rangeEnd) and self.have:
            self.locked = True
            out.drawings.append(DrawBox(NQPREC_ZONE, self.or_start_ms, self.hi, bar.time, self.lo, _ZONE,
                                        fill_color=with_alpha(_ZONE, 30), obj_id=f"nqp.z.{self.or_start_ms}", text="OR"))

        # ---- 5. filtre ------------------------------------------------------------------ #
        a, al = self.atr.update(bar), self.atr_long.update(bar)
        if a is not None and al is not None:
            self.atr_val = a
            self.regime = a / al if al > 0 else float("nan")
        self.vols.append(float(bar.volume))
        if len(self.vols) == self.vols.maxlen:
            m = sum(self.vols) / len(self.vols)
            self.rvol = float(bar.volume) / m if m > 0 else float("nan")
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
