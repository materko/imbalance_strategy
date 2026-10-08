"""Engine DAILY OPEN 1.0 — prieraz nad zavretím polnoci NY (podľa videa Ali Caseyho).

Priebeh (na každom uzavretom bare grafu, čas New York podľa ZAVRETIA baru):

  1. **úroveň**: bar, ktorý sa zavrie v čase `refH:refM` (video: polnoc), dá úroveň = jeho close;
     začína nový deň (počítadlo obchodov, nevyplnený order z predošlého dňa sa zruší),
  2. **noc** (`breakMode = before`): pred začiatkom okna vstupu musí cena prekročiť úroveň,
  3. **vstup** od `entryStartH:M` do `entryEndH:M`: long nad úrovňou + `breakPts` — stop order na tej
     cene (`entryMode = stop`, platí do konca okna) alebo market na zavretí baru nad ňou (`close`);
     pri `tradeDirection = Both / Short only` short zrkadlovo pod úrovňou − `breakPts`,
  4. **výstup**: stop `slPts` od vstupu, cieľ `tpPts` (0 = bez cieľa) a pri `useExit` zatvorenie na zavretí baru
     v čase `exitH:exitM` (video: 16:00, koniec dennej seansy NY).

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import (DrawBox, DrawCommand, DrawDelete, DrawKind, DrawLabel, DrawLine, DrawUpdate, LabelStyle,
                                   LineStyle, with_alpha)
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

from .config import BreakMode, DailyOpenConfig, EntryMode
from .drawing import DO_BREAK, DO_ENTRY, DO_LEVEL

__all__ = ["DailyOpenEngine"]

NY = ZoneInfo("America/New_York")
_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_LEVEL_COLOR = "#f59e0b"
_BREAK_COLOR = "#38bdf8"
#: bez cieľa sa TP položí tak ďaleko, že ho cena prakticky nedosiahne (rovnako ako VWAP ORB)
_NO_TP_R = 100.0


@dataclass(slots=True)
class _Day:
    level: float
    day: date
    ref_t: int                 #: čas zavretia baru úrovne (ms)
    broke_up: bool = False     #: cena bola nad úrovňou pred oknom vstupu
    broke_dn: bool = False
    trades: int = 0


class DailyOpenEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: DailyOpenConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=4, atr_len=14)
        self.required_history = 1
        self.d: _Day | None = None
        #: nevyplnený vstupný order: (id, index baru, smer)
        self._pending: tuple[str, int, Direction] | None = None
        self._entry_day: date | None = None
        #: boxy TP / SL posledného obchodu: (čas signálu, pozícia už bola otvorená)
        self._box: tuple[int, bool] | None = None

    # ------------------------------------------------------------------ #

    def _plan(self, long: bool, entry: float) -> TradePlan | None:
        cfg = self.cfg
        sl = cfg.slPts.resolve(self.inst, price=entry)
        if sl < self.inst.tick_size:
            return None
        tp_pts = cfg.tpPts.resolve(self.inst, price=entry)
        tp = tp_pts if tp_pts > 0 else sl * _NO_TP_R
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        stop = entry - sl if long else entry + sl
        take = entry + tp if long else entry - tp
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    def _cancel(self, out: EngineOutput, idx: int, reason: str) -> None:
        if self._pending is not None:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], idx, reason=reason))
            self._pending = None
            if self._box is not None and not self._box[1]:   # order sa nevyplnil — jeho boxy a štítok preč
                t0 = self._box[0]
                out.drawings.extend(DrawDelete(f"do.{k}.{t0}") for k in ("tp", "sl", "e"))
            self._box = None

    def _boxes(self, out: EngineOutput, bar: Bar, plan: TradePlan) -> None:
        end = bar.time + self.step_ms
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR),
                                   (DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR)):
            top, bot = max(plan.entry, level), min(plan.entry, level)
            if kind == DrawKind.TP_BOX and self.cfg.tpPts.value <= 0:
                top, bot = (plan.entry + plan.sl_distance, plan.entry) if plan.direction is Direction.LONG \
                    else (plan.entry, plan.entry - plan.sl_distance)   # bez cieľa: box 1R, len na orientáciu
            out.drawings.append(DrawBox(kind, bar.time, top, end, bot, color, fill_color=with_alpha(color, 80),
                                        obj_id=f"do.{kind[:2]}.{bar.time}",
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
        self._box = (bar.time, False)

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, long: bool, entry: float, order_type: OrderType,
               day: _Day) -> None:
        plan = self._plan(long, entry)
        if plan is None:
            return
        oid = f"do:{idx}"
        kind = "stop" if order_type is OrderType.STOP else "close"
        out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=plan.direction, plan=plan,
                                      order_type=order_type,
                                      reason=f"prieraz zavretia {self.cfg.refH}:{self.cfg.refM:02d} "
                                             f"{day.level:g} {'+' if long else '−'} {self.cfg.breakPts.value:g} ({kind})"))
        self._pending = (oid, idx, plan.direction) if order_type is not OrderType.MARKET else None
        self._entry_day = day.day
        day.trades += 1
        self._boxes(out, bar, plan)
        out.drawings.append(DrawLabel(
            DO_ENTRY, bar.time, bar.low if long else bar.high,
            f"{'LONG' if long else 'SHORT'} {'stop ' + format(entry, 'g') if order_type is OrderType.STOP else ''}".strip(),
            "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"do.e.{bar.time}"))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        end = bar.time + self.step_ms
        local = datetime.fromtimestamp(end / 1000, tz=NY)
        cmin = local.hour * 60 + local.minute
        today = local.date()
        flat = ctx.position_size == 0.0

        # vyplnený order už nečaká; boxy rastú, kým obchod beží. Order otvorený aj zavretý vnútri
        # jedného baru adaptér hlási cez `open_order_ids` pri nulovej pozícii.
        filled = not flat or (self._pending is not None and self._pending[0] in ctx.open_order_ids)
        if filled:
            self._pending = None
        if self._box is not None:
            t0, was_open = self._box
            for kind in ("tp", "sl"):
                out.drawings.append(DrawUpdate(f"do.{kind}.{t0}", "x2_ms", end))
            if filled and not flat:
                self._box = (t0, True)
            elif was_open or filled:
                self._box = None

        # ---- 1. úroveň ---------------------------------------------------- #
        if cmin == cfg.ref_minutes:
            self._cancel(out, idx, "nový deň")
            self.d = _Day(bar.close, today, end)
            if cfg.showLevels:
                out.drawings.append(DrawLine(DO_LEVEL, end, bar.close, end, bar.close, _LEVEL_COLOR, width=2,
                                             obj_id=f"do.l.{end}", text=f"zavretie {cfg.refH}:{cfg.refM:02d}"))
                b = cfg.breakPts.resolve(self.inst, price=bar.close)
                for sign, tag in ((1, "u"), (-1, "d")):
                    if (sign == 1 and cfg.allow_long) or (sign == -1 and cfg.allow_short):
                        y = bar.close + sign * b
                        out.drawings.append(DrawLine(DO_BREAK, end, y, end, y, _BREAK_COLOR, style=LineStyle.DASHED,
                                                     obj_id=f"do.b{tag}.{end}", text=f"prieraz {'+' if sign == 1 else '−'}{b:g}"))
            return out
        d = self.d
        if d is None:
            return out
        same_day = today == d.day
        if cfg.showLevels and same_day and cmin <= max(cfg.exit_minutes, cfg.entry_end_minutes):
            for oid in (f"do.l.{d.ref_t}", f"do.bu.{d.ref_t}", f"do.bd.{d.ref_t}"):
                out.drawings.append(DrawUpdate(oid, "x2_ms", end))

        # ---- 4. výstup v čase -------------------------------------------- #
        if not flat:
            if cfg.useExit and self._entry_day is not None and (today != self._entry_day or cmin >= cfg.exit_minutes):
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                                  reason=f"výstup {cfg.exitH}:{cfg.exitM:02d}"))
            return out

        # ---- 2. noc: prekročenie úrovne pred oknom ----------------------- #
        if same_day and cmin <= cfg.entry_start_minutes:
            d.broke_up = d.broke_up or bar.high > d.level
            d.broke_dn = d.broke_dn or bar.low < d.level

        in_window = same_day and cfg.entry_start_minutes <= cmin < cfg.entry_end_minutes
        if not in_window:
            self._cancel(out, idx, "koniec okna vstupu")
            return out
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return out

        # ---- 3. vstup ---------------------------------------------------- #
        b = cfg.breakPts.resolve(self.inst, price=bar.close)
        up, dn = d.level + b, d.level - b
        ok_long = cfg.allow_long and (cfg.breakMode is BreakMode.ANY or d.broke_up)
        ok_short = cfg.allow_short and (cfg.breakMode is BreakMode.ANY or d.broke_dn)
        if cfg.entryMode is EntryMode.CLOSE:
            if d.trades >= cfg.maxTradesPerDay:
                return out
            if ok_long and bar.close > up:
                self._enter(out, bar, idx, True, bar.close, OrderType.MARKET, d)
            elif ok_short and bar.close < dn:
                self._enter(out, bar, idx, False, bar.close, OrderType.MARKET, d)
            return out
        # stop order: strana podľa toho, kde je cena voči úrovni (pri jednom smere vždy tá jedna)
        want_long = ok_long and (not ok_short or bar.close >= d.level)
        want_short = ok_short and not want_long
        if self._pending is not None:
            if (self._pending[2] is Direction.LONG) == want_long and (want_long or want_short):
                return out   # order stojí na správnej strane
            self._cancel(out, idx, "cena prešla na druhú stranu úrovne")
            d.trades -= 1    # zrušený nevyplnený order sa nepočíta
        if d.trades >= cfg.maxTradesPerDay:
            return out
        if want_long:
            self._enter(out, bar, idx, True, up, OrderType.STOP, d)
        elif want_short:
            self._enter(out, bar, idx, False, dn, OrderType.STOP, d)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
