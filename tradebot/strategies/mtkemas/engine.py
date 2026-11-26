"""Engine MTK EMAS 1.0 — kríženie kĺzavých priemerov bar po bare (pravidlá štúdie Mac mini, iCloud KLZAKY-STUDIA).

Na každom uzavretom bare grafu:

  1. ATR (RMA true range) a priemer(y) dostanú bar,
  2. znamienko rozdielu (price: zavretie − priemer; cross: rýchly − pomalý); kríženie = zmena z nenulového
     na opačné nenulové (nula medzi nimi kríženie nie je — ako štúdia),
  3. pri krížení: otvorená pozícia proti smeru sa zavrie (`exitOnSignal`), potom vstup v smere kríženia,
     ak ho smer pustí — market na zavretí, stop `slAtr` × ATR, cieľ `rrTarget` R (inak ďaleko), trailing
     `trailAtr` × ATR od `trailFromR` R a zámok na vstup pri `beAtR` R (`TrailingPlan`).

Filter EMA 200 robí spoločný obal vstupov (`trendFilter`). Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawUpdate, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import MaType, MtkEmasConfig, SignalMode
from .drawing import MTKEMAS_ENTRY
from .ma import Atr, make_ma

__all__ = ["MtkEmasEngine", "NO_TP_R", "NO_TRAIL"]

_LONG = "#10b981"
_SHORT = "#ef4444"
#: bez cieľa: TP tak ďaleko, že ho cena nedosiahne
NO_TP_R = 100.0
#: aktivácia trailingu, ktorá nenastane (zámok bez trailingu)
NO_TRAIL = 1e12


class MtkEmasEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: MtkEmasConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        kind = MaType(cfg.maType).value
        self.slow = make_ma(kind, int(cfg.slowLen))
        self.fast = make_ma(kind, int(cfg.fastLen)) if SignalMode(cfg.signalMode) is SignalMode.CROSS else None
        self.atr = Atr(int(cfg.atrLen))
        self.history = BarHistory(maxlen=4, atr_len=int(cfg.atrLen))
        self.prev_sgn = 0
        need = 3 * max(int(cfg.slowLen), int(cfg.fastLen)) + int(cfg.atrLen) + 10
        self.warmup = Warmup(self.tf).add(f"priemer {kind.upper()} {int(cfg.slowLen)}", need)
        self.required_history = self.warmup.chart_bars
        self.boxes: list[str] = []
        self.was_in = False

    # ------------------------------------------------------------------ #

    def _track(self, out: EngineOutput, bar: Bar, ctx: MarketContext) -> None:
        if not self.boxes:
            return
        for oid in self.boxes:
            out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
        if ctx.position_size != 0.0:
            self.was_in = True
        elif self.was_in:
            self.boxes, self.was_in = [], False

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, long: bool, atr: float) -> None:
        cfg, inst = self.cfg, self.inst
        s = 1 if long else -1
        c = bar.close
        risk = float(cfg.slAtr) * atr
        if risk < inst.tick_size * 2:
            return
        rr = float(cfg.rrTarget)
        take = c + s * (rr if rr > 0 else NO_TP_R) * risk
        trailing = None
        if float(cfg.trailAtr) > 0 or float(cfg.beAtR) > 0:
            act = float(cfg.trailFromR) * risk if float(cfg.trailAtr) > 0 else NO_TRAIL
            off = float(cfg.trailAtr) * atr
            trailing = TrailingPlan(activation_price_distance=act, offset_price_distance=off,
                                    activation_ticks=act / inst.tick_size, offset_ticks=off / inst.tick_size,
                                    lock_activation_distance=float(cfg.beAtR) * risk if float(cfg.beAtR) > 0 else 0.0,
                                    lock_level_distance=0.0)
        qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, risk)
        if qty <= 0:
            return
        plan = TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=inst.round_price(c),
                         stop_loss=inst.round_price(c - s * risk), take_profit=inst.round_price(take), qty=qty,
                         sl_distance=risk, trailing=trailing)
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"mtkemas:{idx}", idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.MARKET,
                                      reason=f"MTK EMAS {'long' if long else 'short'}: kríženie {MaType(cfg.maType).value.upper()}"))
        t = bar.time + self.step_ms          # market sa plní na otvorení ďalšej sviečky
        end = t + self.step_ms
        self.boxes, self.was_in = [], False
        levels = [(DrawKind.SL_BOX, plan.stop_loss, _SHORT)]
        if rr > 0:
            levels.insert(0, (DrawKind.TP_BOX, plan.take_profit, _LONG))
        for kind, level, color in levels:
            oid = f"mtkemas.{kind[:2]}.{t}"
            out.drawings.append(DrawBox(kind, t, max(plan.entry, level), end, min(plan.entry, level), color,
                                        fill_color=with_alpha(color, 80), obj_id=oid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(oid)
        out.drawings.append(DrawLabel(MTKEMAS_ENTRY, t, plan.entry, "EMAS long" if long else "EMAS short", "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"mtkemas.e.{t}"))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        cfg, out = self.cfg, EngineOutput()
        self.history.append(bar)
        idx = self.history.bar_index
        self._track(out, bar, ctx)
        pos = ctx.position_size
        atr = self.atr.push(bar.high, bar.low, bar.close)
        slow = self.slow.push(bar.close, bar.volume)
        if self.fast is not None:
            fast = self.fast.push(bar.close, bar.volume)
            diff = None if fast is None or slow is None else fast - slow
        else:
            diff = None if slow is None else bar.close - slow
        sgn = 0 if diff is None else (1 if diff > 0 else (-1 if diff < 0 else 0))
        prev, self.prev_sgn = self.prev_sgn, sgn
        if prev == 0 or sgn == 0 or sgn == prev:
            return out
        long = sgn > 0
        closed = False
        if pos != 0.0 and (pos > 0) != long and cfg.exitOnSignal:
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason="opačné kríženie"))
            closed = True
        if pos != 0.0 and not closed:
            return out
        if (long and not cfg.allow_long) or (not long and not cfg.allow_short) or atr <= 0:
            return out
        self._enter(out, bar, idx, long, atr)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
