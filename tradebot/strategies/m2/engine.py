"""Engine METODA 2 (M2) 1.0 — posledná opačná sviečka pred pohybom, potvrdenie celým telom, limitka na jej hrane.

Priebeh na každom uzavretom bare grafu:

  1. **vyplnenie** — čakajúca limitka sa vyplnila (pozícia alebo `open_order_ids`) → obchod, TP / SL box,
  2. **zánik setupu** — bez vyplnenia: sviečka zavrela za stopom (M2 neplatí), prešlo `limitMaxBars`, alebo
     (`cancelAtTarget`) cena došla k cieľu → zrušiť,
  3. **potvrdenie** — telo tejto sviečky je celé nad poslednou negatívnou sviečkou (min(open, close) > jej high)
     → long M2; celé pod poslednou pozitívnou (max(open, close) < jej low) → short M2; M2 sa tým spotrebuje;
     kvalita (rozšírenie): potvrdenie do `confirmMaxBars` sviečok, telo aspoň `minImpulseAtr` ATR,
  4. **kandidáti** — sviečka so zavretím pod 50 % rozsahu je nová posledná negatívna, nad 50 % nová posledná
     pozitívna (farba nerozhoduje); pri `swingBars` platí len, keď je jej low / high extrémom posledných sviečok (inak setup tej strany zanikne),
  5. **limitka** — bez pozície na potvrdenú M2 (ak sedí trend EMA, okno a limit obchodov): long limit na high M2,
     stop pod low M2 − `slTicks` − `slBufferAtr`, cieľ RR, limitka voliteľne `entryPct` % hlboko v M2, riziko
     v hraniciach `minRiskAtr`–`maxRiskAtr`; novšia potvrdená M2 nahradí čakajúcu.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawUpdate, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup, ema_bars

from .config import M2Config
from .drawing import M2_ENTRY, M2_ZONE

__all__ = ["M2Engine"]

NY = ZoneInfo("America/New_York")
_LONG = "#10b981"
_SHORT = "#ef4444"
_ZONE = "#3b82f6"


class _Ema:
    """Pine `ta.ema`: prvá hodnota = SMA prvých `n` zavretí, potom alpha = 2 / (n + 1)."""

    __slots__ = ("n", "alpha", "count", "total", "value")

    def __init__(self, n: int) -> None:
        self.n = max(1, int(n))
        self.alpha = 2.0 / (self.n + 1)
        self.count = 0
        self.total = 0.0
        self.value = 0.0

    def update(self, x: float) -> None:
        self.count += 1
        if self.count < self.n:
            self.total += x
        elif self.count == self.n:
            self.value = (self.total + x) / self.n
        else:
            self.value += self.alpha * (x - self.value)

    @property
    def ready(self) -> bool:
        return self.count >= self.n


class M2Engine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: M2Config, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=max(4, int(cfg.swingBars) + 1), atr_len=14)
        self.emas = [_Ema(n) for n in cfg.emas]
        need = ema_bars(max(cfg.emas)) if cfg.useEmaTrend else 2
        self.warmup = Warmup(self.chart_tf_minutes).add(f"EMA {max(cfg.emas)}", need)
        self.required_history = max(1, self.warmup.chart_bars)
        #: (čas, high, low, bar_index) poslednej negatívnej / pozitívnej sviečky
        self.last_neg: tuple[int, float, float, int] | None = None
        self.last_pos: tuple[int, float, float, int] | None = None
        #: čakajúca limitka: id, idx, plán, M2 (čas, high, low), bar potvrdenia
        self.pending: tuple[str, int, TradePlan, tuple[int, float, float], int] | None = None
        self.pending_ms = 0
        self.boxes: list[str] = []
        self.was_in = False
        self.day = None
        self.trades = 0

    # ------------------------------------------------------------------ #

    @staticmethod
    def _in(m: int, a: int, b: int) -> bool:
        return a <= m < b if a < b else (m >= a or m < b)

    def _trend(self, close: float) -> int:
        """+1 EMA zoradené nahor, −1 nadol, 0 nie; 2 = filter vypnutý (oba smery)."""
        cfg = self.cfg
        if not cfg.useEmaTrend:
            return 2
        if not all(e.ready for e in self.emas):
            return 0
        v = [e.value for e in self.emas]
        if all(v[i] > v[i + 1] for i in range(len(v) - 1)) and (not cfg.emaNeedClose or close > v[0]):
            return 1
        if all(v[i] < v[i + 1] for i in range(len(v) - 1)) and (not cfg.emaNeedClose or close < v[0]):
            return -1
        return 0

    def _plan(self, long: bool, m2: tuple[int, float, float, int]) -> TradePlan | None:
        cfg, inst = self.cfg, self.inst
        _t, hi, lo, _i = m2
        atr = self.history.atr
        sl = int(cfg.slTicks) * inst.tick_size + float(cfg.slBufferAtr) * atr
        depth = float(cfg.entryPct) / 100.0 * (hi - lo)
        entry = inst.round_price(hi - depth if long else lo + depth)
        stop = inst.round_price(lo - sl if long else hi + sl)
        risk = abs(entry - stop)
        if risk < inst.tick_size:
            return None
        if cfg.minRiskAtr > 0 and (atr <= 0 or risk < cfg.minRiskAtr * atr):
            return None
        if cfg.maxRiskAtr > 0 and (atr <= 0 or risk > cfg.maxRiskAtr * atr):
            return None
        take = entry + cfg.rrRatio * risk if long else entry - cfg.rrRatio * risk
        qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, risk)
        if qty <= 0:
            qty = float(inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=entry,
                         stop_loss=stop, take_profit=inst.round_price(take), qty=qty, sl_distance=risk)

    def _filled(self, out: EngineOutput, bar: Bar) -> None:
        _oid, _at, plan, m2, _conf = self.pending
        self.pending = None
        self.trades += 1
        long = plan.direction is Direction.LONG
        self.boxes, self.was_in = [], False
        x1, end = self.pending_ms, bar.time + self.step_ms
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG), (DrawKind.SL_BOX, plan.stop_loss, _SHORT)):
            bid = f"m2.{kind[:2]}.{x1}"
            out.drawings.append(DrawBox(kind, x1, max(plan.entry, level), end, min(plan.entry, level), color,
                                        fill_color=with_alpha(color, 60), obj_id=bid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(bid)
        out.drawings.append(DrawLabel(M2_ENTRY, bar.time, plan.entry, "LONG M2" if long else "SHORT M2", "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"m2.e.{bar.time}"))

    def _cancel(self, out: EngineOutput, reason: str) -> None:
        oid, at, _p, _m, _c = self.pending
        out.orders.append(OrderIntent(OrderAction.CANCEL, oid, at, reason=reason))
        self.pending = None

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        for e in self.emas:
            e.update(bar.close)
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

        # ---- 1. vyplnenie limitky --------------------------------------------- #
        if self.pending is not None and (pos != 0.0 or self.pending[0] in ctx.open_order_ids):
            self._filled(out, bar)
        elif self.pending is not None and pos == 0.0:
            # ---- 2. zánik setupu bez vyplnenia -------------------------------- #
            plan, conf = self.pending[2], self.pending[4]
            long = plan.direction is Direction.LONG
            if (bar.close < plan.stop_loss) if long else (bar.close > plan.stop_loss):
                self._cancel(out, "sviečka zavrela za stopom — M2 neplatí")
            elif int(cfg.limitMaxBars) > 0 and idx - conf >= int(cfg.limitMaxBars):
                self._cancel(out, f"limitka čakala {cfg.limitMaxBars} sviečok")
            elif cfg.cancelAtTarget and ((bar.high >= plan.take_profit) if long else (bar.low <= plan.take_profit)):
                self._cancel(out, "cena došla k cieľu bez vyplnenia — pohyb ušiel")

        # ---- 3. potvrdenie M2 telom tejto sviečky ---------------------------- #
        cmax = int(cfg.confirmMaxBars)
        if cmax > 0:
            if self.last_neg is not None and idx - self.last_neg[3] > cmax:
                self.last_neg = None
            if self.last_pos is not None and idx - self.last_pos[3] > cmax:
                self.last_pos = None
        body_lo, body_hi = min(bar.open, bar.close), max(bar.open, bar.close)
        impulse = cfg.minImpulseAtr <= 0 or body_hi - body_lo >= cfg.minImpulseAtr * self.history.atr > 0
        confirmed: tuple[bool, tuple[int, float, float, int]] | None = None
        if self.last_neg is not None and body_lo > self.last_neg[1]:
            if impulse:
                confirmed = (True, self.last_neg)
            self.last_neg = None
        if self.last_pos is not None and body_hi < self.last_pos[2]:
            if impulse:
                confirmed = (False, self.last_pos)
            self.last_pos = None

        # ---- 4. kandidáti: posledná negatívna / pozitívna sviečka ------------- #
        mid = bar.low + (bar.high - bar.low) / 2.0
        if bar.high > bar.low:
            n = min(int(cfg.swingBars), len(self.history))
            if bar.close < mid:
                ok = n <= 1 or all(bar.low <= self.history[k].low for k in range(1, n))
                self.last_neg = (bar.time, bar.high, bar.low, idx) if ok else None
            elif bar.close > mid:
                ok = n <= 1 or all(bar.high >= self.history[k].high for k in range(1, n))
                self.last_pos = (bar.time, bar.high, bar.low, idx) if ok else None

        # ---- 5. limitka na potvrdenú M2 --------------------------------------- #
        if pos == 0.0 and confirmed is not None:
            long, m2 = confirmed
            trend = self._trend(bar.close)
            ok = (cfg.allowLong and trend in (1, 2)) if long else (cfg.allowShort and trend in (-1, 2))
            if ok and cfg.useWindow:
                nxt = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
                ok = self._in(nxt.hour * 60 + nxt.minute, cfg.entry_start, cfg.entry_end)
            if ok and int(cfg.maxTradesPerDay) > 0 and self.trades >= int(cfg.maxTradesPerDay):
                ok = False
            plan = self._plan(long, m2) if ok else None
            if plan is not None:
                if self.pending is not None:
                    self._cancel(out, "novšia potvrdená M2")
                oid = f"m2:{idx}"
                out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=plan.direction, plan=plan,
                                              order_type=OrderType.LIMIT,
                                              reason=f"M2 {'long' if long else 'short'} potvrdená — limit na "
                                                     f"{'high' if long else 'low'} M2"))
                self.pending = (oid, idx, plan, m2, idx)
                self.pending_ms = bar.time
                if cfg.showZones:
                    out.drawings.append(DrawBox(M2_ZONE, m2[0], m2[1], bar.time + self.step_ms, m2[2], _ZONE,
                                                fill_color=with_alpha(_ZONE, 50), obj_id=f"m2.z.{m2[0]}",
                                                text="M2"))
        elif self.pending is not None and pos != 0.0:
            self.pending = None
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
