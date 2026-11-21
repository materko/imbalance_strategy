"""Engine IB RETRACE 1.0 — prieraz Initial Balance a vstup na návrate do IB (video IB Lab „Max Retracement Price“).

Čas = otvorenie baru v New Yorku. Na každom uzavretom bare:

  1. **nový deň** (dátum NY) — zrušiť čakajúcu limitku, vynulovať IB a stav dňa,
  2. **IB** — bary `ibStart` ≤ t < koniec IB rozšíria high / low a nič ďalšie,
  3. **IB hotový** — deň v týždni a šírka IB rozhodnú, či sa v ten deň obchoduje,
  4. **limitka sa vyplnila?** — pozícia alebo id v otvorených obchodoch,
  5. **koniec** — `closeAtEnd` a zavretie baru o `exitTime` a neskôr: pozíciu zavrieť,
  6. **čakajúca limitka** — zrušiť pri `lastEntry`, pri prieraze druhej strany IB a keď cena došla do cieľa bez návratu,
  7. **prieraz** — prvé zavretie za IB rozhodne o dni: v okne `breakFrom`–`breakTo` a povolenom smere vstup
     (limitka na `entryRetr` alebo market), stop na `slRetr`, cieľ extenzia / RR; inak v ten deň nič.

Úroveň x (zlomok šírky IB) leží pri longu na IB high − x × IB, pri shorte na IB low + x × IB.
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
from tradebot.core.warmup import Warmup

from .config import EntryMode, IbRetConfig, TpMode
from .drawing import IBRET_ENTRY, IBRET_ZONE

__all__ = ["IbRetEngine"]

NY = ZoneInfo("America/New_York")
_LONG = "#22c55e"
_SHORT = "#ef4444"
_ZONE = "#2196f3"

_WAIT, _DONE = 0, 1   # stav dňa: čaká na prieraz / o dni je rozhodnuté


def _hm(v: int) -> int:
    return (int(v) // 100) * 60 + int(v) % 100


class IbRetEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: IbRetConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        self.history = BarHistory(maxlen=4, atr_len=14)
        self.warmup = Warmup(self.tf)
        self.required_history = 1
        self.day = None
        self.ib_high = float("-inf")
        self.ib_low = float("inf")
        self.ib_start_ms = 0
        self.ib_ready = False
        self.state = _WAIT
        self.pending: str | None = None      # id limitky, kým sa nevyplní
        self.pend_long = True
        self.pend_take = 0.0
        self.boxes: list[str] = []
        self.was_in = False

    # ------------------------------------------------------------------ #

    def _cancel(self, out: EngineOutput, idx: int, reason: str) -> None:
        out.orders.append(OrderIntent(OrderAction.CANCEL, self.pending, idx, reason=reason))
        self.pending = None
        self.boxes, self.was_in = [], False

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, long: bool) -> None:
        cfg, inst = self.cfg, self.inst
        rng = self.ib_high - self.ib_low
        edge = self.ib_high if long else self.ib_low
        s = 1 if long else -1
        stop = inst.round_price(edge - s * float(cfg.slRetr) * rng - s * int(cfg.slBufferTicks) * inst.tick_size)
        if cfg.entryMode is EntryMode.BREAKOUT:
            entry, order_type = bar.close, OrderType.MARKET
        else:
            entry, order_type = inst.round_price(edge - s * float(cfg.entryRetr) * rng), OrderType.LIMIT
        risk = abs(entry - stop)
        if risk < inst.tick_size * 2:
            return
        if cfg.tpMode is TpMode.EXT:
            take = inst.round_price(edge + s * float(cfg.tpExt) * rng)
        else:
            take = inst.round_price(entry + s * float(cfg.rr) * risk)
        reward = s * (take - entry)
        if reward <= 0 or reward < float(cfg.minRR) * risk - 1e-9:
            return
        qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, risk)
        if qty <= 0:
            return
        plan = TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=entry, stop_loss=stop,
                         take_profit=take, qty=qty, sl_distance=risk)
        oid = f"ibret:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=plan.direction, plan=plan,
                                      order_type=order_type,
                                      reason=f"IB RETRACE {'long' if long else 'short'}: IB {self.ib_low:g}–{self.ib_high:g}"))
        if order_type is OrderType.LIMIT:
            self.pending, self.pend_long, self.pend_take = oid, long, take
        t = bar.time + self.step_ms          # order platí od otvorenia ďalšej sviečky
        end = t + self.step_ms
        self.boxes, self.was_in = [], False
        for kind, level, color in ((DrawKind.TP_BOX, take, _LONG), (DrawKind.SL_BOX, stop, _SHORT)):
            bid = f"ibret.{kind[:2]}.{t}"
            out.drawings.append(DrawBox(kind, t, max(entry, level), end, min(entry, level), color,
                                        fill_color=with_alpha(color, 60), obj_id=bid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(bid)
        out.drawings.append(DrawLabel(IBRET_ENTRY, t, entry, "IB long" if long else "IB short", "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"ibret.e.{t}"))

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
        tc = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
        close_mins = tc.hour * 60 + tc.minute

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
            if self.pending is not None:
                self._cancel(out, idx, "nový deň")
            elif pos == 0.0:
                self.boxes, self.was_in = [], False      # obchod otvorený aj zavretý v jednej sviečke — boxy už nerastú
            self.ib_high, self.ib_low = float("-inf"), float("inf")
            self.ib_ready = False
            self.state = _WAIT

        ib_start = _hm(cfg.ibStart)
        ib_end = ib_start + int(cfg.ibMinutes)

        # ---- 2. IB ---------------------------------------------------------------- #
        if not self.ib_ready and ib_start <= mins < ib_end:
            if self.ib_high == float("-inf"):
                self.ib_start_ms = bar.time
            self.ib_high = max(self.ib_high, bar.high)
            self.ib_low = min(self.ib_low, bar.low)
            if cfg.drawRange:
                out.drawings.append(DrawBox(IBRET_ZONE, self.ib_start_ms, self.ib_high,
                                            self.ib_start_ms + int(cfg.ibMinutes) * 60_000, self.ib_low, _ZONE,
                                            fill_color=with_alpha(_ZONE, 38), obj_id=f"ibret.z.{self.ib_start_ms}",
                                            text="IB"))
            return out

        # ---- 3. IB hotový ------------------------------------------------------------ #
        if not self.ib_ready and mins >= ib_end and self.ib_high != float("-inf"):
            self.ib_ready = True
            rng = self.ib_high - self.ib_low
            wd = t.weekday()
            days = (cfg.tradeMon, cfg.tradeTue, cfg.tradeWed, cfg.tradeThu, cfg.tradeFri)
            if rng <= 0 or wd > 4 or not days[wd] \
                    or (float(cfg.minIbPoints) > 0 and rng < float(cfg.minIbPoints)) \
                    or (float(cfg.maxIbPoints) > 0 and rng > float(cfg.maxIbPoints)):
                self.state = _DONE
        if not self.ib_ready:
            return out

        # ---- 4. limitka sa vyplnila? ------------------------------------------------- #
        if self.pending is not None and (pos != 0.0 or self.pending in ctx.open_order_ids):
            self.pending = None

        # ---- 5. koniec -------------------------------------------------------------- #
        if cfg.closeAtEnd and pos != 0.0 and close_mins >= _hm(cfg.exitTime):
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason=f"koniec {int(cfg.exitTime):04d} NY"))
            return out

        # ---- 6. čakajúca limitka ------------------------------------------------------- #
        if self.pending is not None:
            long = self.pend_long
            reason = None
            if close_mins >= _hm(cfg.lastEntry):
                reason = "koniec vstupov"
            elif (bar.low < self.ib_low) if long else (bar.high > self.ib_high):
                reason = "prieraz druhej strany IB"
            elif (bar.high >= self.pend_take) if long else (bar.low <= self.pend_take):
                reason = "cieľ bez návratu"
            if reason is not None:
                self._cancel(out, idx, reason)
            return out
        if self.state != _WAIT:
            return out

        # ---- 7. prieraz ---------------------------------------------------------------- #
        up = bar.close > self.ib_high
        down = bar.close < self.ib_low
        if not (up or down):
            return out
        self.state = _DONE                                # o dni rozhoduje prvý prieraz
        hhmm = t.hour * 100 + t.minute
        if not (int(cfg.breakFrom) <= hhmm <= int(cfg.breakTo)):
            return out
        if (up and not cfg.allow_long) or (down and not cfg.allow_short):
            return out
        self._enter(out, bar, idx, up)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
