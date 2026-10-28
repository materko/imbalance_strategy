"""Engine NB 1.0 — prieraz konsolidácie na grafe v smere trendu vyššieho TF (SMA 10 / 20).

Priebeh na každom uzavretom bare grafu:

  1. **vyplnenie** — čakajúci stop order sa vyplnil (pozícia alebo `open_order_ids`) → obchod, TP / SL box,
  2. **držanie** — pozícia otvorená dlhšie než `maxHoldHours` sa zavrie trhom,
  3. **vyšší TF** — bary grafu sa skladajú do sviečok `htfTF` (zarovnané na epochu ako `tradebot.core.candles`);
     na uzavretej sviečke sa posunú SMA trendu a potvrdia swingy (`pivotLen` sviečok po oboch stranách),
  4. **stop order** — bez pozície, keď sa ďalší bar otvára v okne vstupu a v povolený deň: posledných
     `consBars` sviečok grafu je konsolidácia (šírka v ATR), trend vyššieho TF a SMA grafu ukazujú ten istý
     smer → stop order za hranou konsolidácie (stop za opačnou hranou + `slBuffer` + 1 tick, cieľ RR),
     ak má cieľ miesto pred najbližším swingom vyššieho TF; inak sa čakajúci order zruší. Order sa
     prekladá, keď sa hranice konsolidácie zmenia.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawUpdate, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup, rma_bars

from .config import NbConfig
from .drawing import NB_ENTRY, NB_ZONE

__all__ = ["NbEngine"]

NY = ZoneInfo("America/New_York")
_LONG = "#10b981"
_SHORT = "#ef4444"
_ZONE = "#8b5cf6"
_HOUR_MS = 3_600_000


def _sma(values, length: int) -> float:
    if len(values) < length:
        return 0.0
    total = 0.0
    for i in range(len(values) - length, len(values)):
        total += values[i]
    return total / length


class NbEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: NbConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.htf_ms = max(int(cfg.htfTF), self.chart_tf_minutes) * 60_000
        self.history = BarHistory(maxlen=int(cfg.consBars) + 2, atr_len=int(cfg.atrLen))
        chart_need = max(int(cfg.consBars), rma_bars(int(cfg.atrLen)), int(cfg.smaSlow)) + 1
        htf_need = int(cfg.smaSlow) + 2 * int(cfg.pivotLen) + 2
        self.warmup = (Warmup(self.chart_tf_minutes)
                       .add(f"konsolidácia, ATR {cfg.atrLen}, SMA {cfg.smaSlow}", chart_need)
                       .add(f"trend {cfg.htfTF}m (SMA {cfg.smaSlow})", htf_need, tf_minutes=self.htf_ms // 60_000))
        self.required_history = max(1, self.warmup.chart_bars)
        self.closes: deque[float] = deque(maxlen=int(cfg.smaSlow))
        self.highs: deque[float] = deque(maxlen=int(cfg.consBars))
        self.lows: deque[float] = deque(maxlen=int(cfg.consBars))
        # vyšší TF
        self.cur: list[float] | None = None          #: rozpracovaná sviečka [open_ms, o, h, l, c]
        self.h_closes: deque[float] = deque(maxlen=int(cfg.smaSlow))
        self.h_bars: deque[tuple[float, float]] = deque(maxlen=2 * int(cfg.pivotLen) + 1)
        self.piv_hi: deque[float] = deque(maxlen=50)
        self.piv_lo: deque[float] = deque(maxlen=50)
        self.h_last_close = 0.0
        # obchod
        self.pending: tuple[str, int, TradePlan, float, float] | None = None   #: id, idx, plán, hi, lo
        self.pending_ms = 0
        self.fill_ms: int | None = None
        self.boxes: list[str] = []
        self.was_in = False
        self.day = None
        self.trades = 0

    # ------------------------------------------------------------------ #

    @staticmethod
    def _in(m: int, a: int, b: int) -> bool:
        return a <= m < b if a < b else (m >= a or m < b)

    # ---- vyšší TF ----------------------------------------------------------- #

    def _feed_htf(self, bar: Bar) -> None:
        bucket = bar.time // self.htf_ms * self.htf_ms
        if self.cur is not None and int(self.cur[0]) != bucket:
            self._push_htf()                    # diera v dátach: predošlá sviečka sa uzavrie až teraz
        if self.cur is None:
            self.cur = [bucket, bar.open, bar.high, bar.low, bar.close]
        else:
            self.cur[2] = max(self.cur[2], bar.high)
            self.cur[3] = min(self.cur[3], bar.low)
            self.cur[4] = bar.close
        if bar.time + self.step_ms >= bucket + self.htf_ms:
            self._push_htf()

    def _push_htf(self) -> None:
        _t, _o, h, l, c = self.cur
        self.cur = None
        self.h_closes.append(c)
        self.h_last_close = c
        self.h_bars.append((h, l))
        p = int(self.cfg.pivotLen)
        if len(self.h_bars) == 2 * p + 1:
            mh, ml = self.h_bars[p]
            others = [self.h_bars[i] for i in range(2 * p + 1) if i != p]
            if all(mh > o[0] for o in others):
                self.piv_hi.append(mh)
            if all(ml < o[1] for o in others):
                self.piv_lo.append(ml)

    def _htf_trend(self) -> int:
        """+1 uptrend, −1 downtrend, 0 bez trendu alebo bez dosť sviečok."""
        cfg = self.cfg
        if not cfg.useHtfTrend:
            return 2                            # oba smery
        if len(self.h_closes) < int(cfg.smaSlow):
            return 0
        f = _sma(self.h_closes, int(cfg.smaFast))
        s = _sma(self.h_closes, int(cfg.smaSlow))
        c = self.h_last_close
        if f > s and (not cfg.htfNeedClose or c > f):
            return 1
        if f < s and (not cfg.htfNeedClose or c < f):
            return -1
        return 0

    # ---- obchod ------------------------------------------------------------- #

    def _plan(self, long: bool, hi: float, lo: float, close: float, atr: float) -> TradePlan | None:
        cfg, inst = self.cfg, self.inst
        off = int(cfg.entryOffsetTicks) * inst.tick_size
        buf = cfg.slBuffer.resolve(inst, price=close, atr=atr) + inst.tick_size
        entry = inst.round_price(hi + off if long else lo - off)
        stop = inst.round_price(lo - buf if long else hi + buf)
        risk = abs(entry - stop)
        if risk < inst.tick_size * 2:
            return None
        take = entry + cfg.rrRatio * risk if long else entry - cfg.rrRatio * risk
        if cfg.useRoom and cfg.roomMinR > 0:
            if long:
                above = [p for p in self.piv_hi if p > entry]
                if above and min(above) - entry < cfg.roomMinR * risk:
                    return None
            else:
                below = [p for p in self.piv_lo if p < entry]
                if below and entry - max(below) < cfg.roomMinR * risk:
                    return None
        qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, risk)
        if qty <= 0:
            qty = float(inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=entry,
                         stop_loss=stop, take_profit=inst.round_price(take), qty=qty, sl_distance=risk)

    def _filled(self, out: EngineOutput, bar: Bar) -> None:
        _oid, _at, plan, hi, lo = self.pending
        self.pending = None
        self.trades += 1
        self.fill_ms = bar.time
        long = plan.direction is Direction.LONG
        self.boxes, self.was_in = [], False
        x1, end = self.pending_ms, bar.time + self.step_ms
        if self.cfg.showZones:
            x0 = x1 - (int(self.cfg.consBars) - 1) * self.step_ms
            out.drawings.append(DrawBox(NB_ZONE, x0, hi, x1 + self.step_ms, lo, _ZONE,
                                        fill_color=with_alpha(_ZONE, 40), obj_id=f"nb.z.{x1}",
                                        text=f"konsolidácia {self.cfg.consBars}"))
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG), (DrawKind.SL_BOX, plan.stop_loss, _SHORT)):
            bid = f"nb.{kind[:2]}.{x1}"
            out.drawings.append(DrawBox(kind, x1, max(plan.entry, level), end, min(plan.entry, level), color,
                                        fill_color=with_alpha(color, 60), obj_id=bid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(bid)
        out.drawings.append(DrawLabel(NB_ENTRY, x1, plan.entry, "LONG prieraz" if long else "SHORT prieraz", "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"nb.e.{x1}"))

    def _cancel(self, out: EngineOutput, reason: str) -> None:
        oid, at, _p, _h, _l = self.pending
        out.orders.append(OrderIntent(OrderAction.CANCEL, oid, at, reason=reason))
        self.pending = None

    def _signal(self, bar: Bar) -> tuple[bool, float, float] | None:
        """(long, hi, lo) konsolidácie, z ktorej sa na ďalšom bare smie vstúpiť; None = nie."""
        cfg, inst = self.cfg, self.inst
        nxt = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
        if not cfg.weekdays[nxt.weekday()]:
            return None
        if not self._in(nxt.hour * 60 + nxt.minute, cfg.entry_start, cfg.entry_end):
            return None
        if int(cfg.maxTradesPerDay) > 0 and self.trades >= int(cfg.maxTradesPerDay):
            return None
        atr = self.history.atr
        if atr <= 0 or len(self.highs) < int(cfg.consBars) or len(self.closes) < int(cfg.smaSlow):
            return None
        hi, lo = max(self.highs), min(self.lows)
        width = hi - lo
        wmin = cfg.consMinWidth.resolve(inst, price=bar.close, atr=atr)
        wmax = cfg.consMaxWidth.resolve(inst, price=bar.close, atr=atr)
        if (wmin > 0 and width < wmin) or (wmax > 0 and width > wmax):
            return None
        trend = self._htf_trend()
        if trend == 0:
            return None
        f = _sma(self.closes, int(cfg.smaFast))
        s = _sma(self.closes, int(cfg.smaSlow))
        c = bar.close
        long_ok = cfg.allowLong and trend in (1, 2) and (not cfg.useChartSma or (c > f and c > s and f > s))
        short_ok = cfg.allowShort and trend in (-1, 2) and (not cfg.useChartSma or (c < f and c < s and f < s))
        if long_ok == short_ok:                 # žiadny smer, alebo (bez filtrov) oba naraz — nevstupuje sa
            return None
        return long_ok, hi, lo

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        self.closes.append(bar.close)
        self.highs.append(bar.high)
        self.lows.append(bar.low)
        idx = self.history.bar_index
        pos = ctx.position_size
        day = datetime.fromtimestamp(bar.time / 1000, tz=NY).date()
        if day != self.day:
            self.day, self.trades = day, 0

        # ---- TP / SL boxy bežiaceho obchodu ---------------------------------- #
        if self.boxes:
            for oid in self.boxes:
                out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
            if pos != 0.0:
                self.was_in = True
            elif self.was_in:
                self.boxes, self.was_in = [], False

        # ---- 1. vyplnenie stop orderu ----------------------------------------- #
        if self.pending is not None and (pos != 0.0 or self.pending[0] in ctx.open_order_ids):
            self._filled(out, bar)
        if pos == 0.0:
            self.fill_ms = None

        # ---- 2. najdlhšie držanie --------------------------------------------- #
        if (pos != 0.0 and cfg.maxHoldHours > 0 and self.fill_ms is not None
                and bar.time + self.step_ms - self.fill_ms >= int(cfg.maxHoldHours) * _HOUR_MS):
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason=f"drží sa {cfg.maxHoldHours} h"))
            self.fill_ms = None

        # ---- 3. vyšší TF ------------------------------------------------------ #
        self._feed_htf(bar)

        # ---- 4. stop order na prieraz konsolidácie ---------------------------- #
        if pos == 0.0 and not out.close_session:
            sig = self._signal(bar)
            plan = None
            if sig is not None:
                plan = self._plan(sig[0], sig[1], sig[2], bar.close, self.history.atr)
            if self.pending is not None:
                old = self.pending[2]
                if plan is None or plan.direction is not old.direction or plan.entry != old.entry \
                        or plan.stop_loss != old.stop_loss:
                    self._cancel(out, "konsolidácia sa zmenila" if plan is not None else "bez setupu")
            if plan is not None and self.pending is None:
                oid = f"nb:{idx}"
                long = plan.direction is Direction.LONG
                out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=plan.direction, plan=plan,
                                              order_type=OrderType.STOP,
                                              reason=f"prieraz konsolidácie {cfg.consBars} sviečok "
                                                     f"{'nahor' if long else 'nadol'} v smere {cfg.htfTF}m"))
                self.pending = (oid, idx, plan, sig[1], sig[2])
                self.pending_ms = bar.time
        elif self.pending is not None and pos != 0.0:
            self.pending = None
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
