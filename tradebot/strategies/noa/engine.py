"""Engine NOA 1.0 — Noise Area (Concretum): vstup pri úniku z pásma šumu, výstup cez VWAP / hranicu alebo o 16:00.

Priebeh dňa (čas New York, seansa 9:30–16:00, minúta = čas **zavretia** baru):

  1. Na každom bare seansy sa uloží |close / open dňa − 1| pre jeho minútu od 9:30; pásmo šumu σ pre minútu
     je priemer z `lookbackDays` predošlých dní (dnešok sa do neho pridá až na konci dňa).
  2. Hranice: horná = max(open, včerajšie zavretie) × (1 + `volMult` × σ), dolná = min(…) × (1 − `volMult` × σ).
  3. Rozhoduje sa **len na kontrolách** — prvý bar, ktorý sa zatvára o `checkEvery`, 2 × `checkEvery`, … minút
     po 9:30 (zdroj: 10:00, 10:30, …). Bez pozície: zavretie nad hornou hranicou = long, pod dolnou = short
     (do `lastEntryMin`). S pozíciou: long sa zavrie, keď zavretie klesne pod max(hornú hranicu, VWAP)
     (`trailVwap`), short zrkadlovo. Medzi kontrolami sa nerobí nič — to je rozdiel oproti posúvanému stopu
     u brokera, ktorý by obchody vyhadzoval na šume.
  4. Bar, ktorý sa zatvára o 16:00, zatvorí pozíciu. Pozícia, ktorá prežila do ďalšieho dňa (skrátená seansa
     pred sviatkom), sa zatvorí na prvom bare seansy.

Pevný stop v pláne obchodu je len poistka `hardStopPct` (zdroj ju nemá). Vstup a výstupy sú market na zavretí
baru (plnia sa na otvorení ďalšieho). Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque

from tradebot.core.drawing import DrawCommand, DrawLine, LineStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ._common import LONG_COLOR, SHORT_COLOR, SessionVwapLite, TradeHelper, close_minute
from .config import NoaConfig
from .drawing import NOA_ENTRY, NOA_LEVEL, NOA_STOP, NOA_VWAP

__all__ = ["NoaEngine"]

_OPEN_MIN = 9 * 60 + 30     # 9:30 New York
_CLOSE_MIN = 16 * 60        # 16:00 New York
_VWAP_COLOR = "#a855f7"
_STOP_COLOR = "#f59e0b"
#: VWAP sa kreslí raz za toľko minút (na 1m grafe by úsečka za každý bar bola zbytočne veľa kresieb)
_VWAP_STEP_MIN = 5
#: `hardStopPct = 0` = poistka tak ďaleko, že ju intraday pohyb nedosiahne
_NO_STOP_PCT = 10.0


class NoaEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: NoaConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        self.history = BarHistory(maxlen=4, atr_len=14)
        #: minúta od 9:30 -> pohyby |close / open − 1| z predošlých dní
        self.hist: dict[int, deque[float]] = {}
        self.today: dict[int, float] = {}
        self.day: tuple[int, int, int] | None = None
        self.open: float | None = None
        #: zavretie predošlej seansy (posledný bar seansy, aj pri skrátenej seanse)
        self.prev_close: float | None = None
        self.last_close: float | None = None
        self.next_check = int(cfg.checkEvery)
        self.vwap = SessionVwapLite()
        self.trades = 0
        self.helper = TradeHelper(inst, self.step_ms, "noa", NOA_ENTRY)
        self._vwap_pt: tuple[int, float] | None = None
        days = int(cfg.lookbackDays) + 2
        self.warmup = Warmup(self.tf).add(f"pásmo šumu {cfg.lookbackDays} dní", days * 1440 // self.tf)
        self.required_history = self.warmup.chart_bars

    # ------------------------------------------------------------------ #

    def sigma(self, mm: int) -> float | None:
        """Pásmo šumu pre minútu `mm` od 9:30 — priemer z predošlých dní (aspoň polovica `lookbackDays`)."""
        d = self.hist.get(mm)
        if not d or len(d) < max(3, int(self.cfg.lookbackDays) // 2):
            return None
        return sum(d) / len(d)

    def bounds(self, mm: int) -> tuple[float, float] | None:
        """(horná, dolná) hranica pásma pre minútu `mm`, alebo ``None``, kým nie je z čoho."""
        sg = self.sigma(mm)
        if sg is None or self.open is None or self.prev_close is None:
            return None
        cfg = self.cfg
        hi_ref = max(self.open, self.prev_close) if cfg.gapAdjust else self.open
        lo_ref = min(self.open, self.prev_close) if cfg.gapAdjust else self.open
        return hi_ref * (1 + cfg.volMult * sg), lo_ref * (1 - cfg.volMult * sg)

    def _new_day(self, day, bar: Bar) -> None:
        if self.day is not None:
            n = int(self.cfg.lookbackDays)
            for k, v in self.today.items():
                self.hist.setdefault(k, deque(maxlen=n)).append(v)
            self.prev_close = self.last_close
        self.today, self.day, self.open, self.trades = {}, day, bar.open, 0
        self.next_check = int(self.cfg.checkEvery)
        self._vwap_pt = None

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        cfg, out = self.cfg, EngineOutput()
        self.history.append(bar)
        idx = self.history.bar_index
        self.helper.track(out, bar, ctx)
        day, m, wd = close_minute(bar, self.step_ms)
        if not (_OPEN_MIN < m <= _CLOSE_MIN) or (cfg.weekdaysOnly and wd >= 5):
            return out
        pos = ctx.position_size
        if day != self.day:
            self._new_day(day, bar)
            if pos != 0.0:
                self.helper.close(out, ctx, idx, "pozícia z predošlého dňa")
                pos = 0.0
        mm = m - _OPEN_MIN
        vw = self.vwap.push(day, bar)
        self.today[mm] = abs(bar.close / self.open - 1.0)
        self.last_close = bar.close
        if cfg.showVwap and vw is not None:
            out.drawings += self._draw_vwap(bar, m, vw)

        # ---- 16:00: koniec seansy --------------------------------------- #
        if m + self.tf > _CLOSE_MIN:
            if pos != 0.0:
                self.helper.close(out, ctx, idx, "koniec seansy 16:00")
            return out

        # ---- kontrola každých checkEvery minút ----------------------------- #
        if mm < self.next_check:
            return out
        self.next_check = (mm // int(cfg.checkEvery) + 1) * int(cfg.checkEvery)
        b = self.bounds(mm)
        if b is None or vw is None:
            return out
        ub, lb = b
        end = bar.time + self.step_ms + int(cfg.checkEvery) * 60_000
        if cfg.showLevels:
            for y, c, n in ((ub, LONG_COLOR, "u"), (lb, SHORT_COLOR, "d")):
                out.drawings.append(DrawLine(NOA_LEVEL, bar.time + self.step_ms, y, end, y, c, style=LineStyle.DOTTED,
                                             obj_id=f"noa.{n}.{bar.time}", text="horná hranica" if n == "u" else "dolná hranica"))
        long_stop = max(ub, vw) if cfg.trailVwap else ub
        short_stop = min(lb, vw) if cfg.trailVwap else lb

        if pos > 0.0:
            if bar.close < long_stop:
                self.helper.close(out, ctx, idx, "zavretie pod hranicou / VWAP")
            elif cfg.showLevels:
                out.drawings.append(self._stop_line(bar, long_stop, end))
            return out
        if pos < 0.0:
            if bar.close > short_stop:
                self.helper.close(out, ctx, idx, "zavretie nad hranicou / VWAP")
            elif cfg.showLevels:
                out.drawings.append(self._stop_line(bar, short_stop, end))
            return out
        if mm > int(cfg.lastEntryMin) or self.trades >= int(cfg.maxTradesPerDay):
            return out
        long = cfg.allow_long and bar.close > ub
        short = cfg.allow_short and bar.close < lb
        if not (long or short):
            return out
        entry = bar.close
        hard = (cfg.hardStopPct or _NO_STOP_PCT) / 100.0 * entry
        stop = entry - hard if long else entry + hard
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, hard)
        plan = self.helper.plan(long, entry, stop, None, qty if qty > 0 else 1.0)
        if plan is None:
            return out
        self.helper.enter(out, bar, idx, plan, "únik z pásma šumu", f"{'LONG' if long else 'SHORT'} šum",
                          show_tp=False)
        self.trades += 1
        if cfg.showLevels:
            out.drawings.append(self._stop_line(bar, long_stop if long else short_stop, end))
        return out

    # ------------------------------------------------------------------ #

    def _stop_line(self, bar: Bar, level: float, end: int) -> DrawLine:
        """Úroveň výstupu do ďalšej kontroly (max(hranica, VWAP) pri longu, min pri shorte)."""
        return DrawLine(NOA_STOP, bar.time + self.step_ms, level, end, level, _STOP_COLOR, style=LineStyle.DASHED,
                        width=2, obj_id=f"noa.stop.{bar.time}", text="výstup na kontrole")

    def _draw_vwap(self, bar: Bar, m: int, vw: float) -> list[DrawCommand]:
        if m % _VWAP_STEP_MIN and self.tf < _VWAP_STEP_MIN:
            return []
        end = bar.time + self.step_ms
        prev, self._vwap_pt = self._vwap_pt, (end, vw)
        if prev is None:
            return []
        return [DrawLine(NOA_VWAP, prev[0], prev[1], end, vw, _VWAP_COLOR, obj_id=f"noa.vwap.{end}", text="VWAP")]

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
