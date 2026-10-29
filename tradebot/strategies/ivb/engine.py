"""Engine IVB 1.0 — Initial Volatility Breakout, prepis Rust stratégie `IvbStrategy` (`rq_sdk`) bar po bare.

Poradie krokov na každom uzavretom bare je to isté ako v predlohe (`on_bar`), čas = otvorenie baru v New Yorku (HHMM):

  1. **nový deň** — pri `flattenEod` zavrieť pozíciu z predošlého dňa, vynulovať IB a počítadlo pokusov,
  2. **koniec dňa** — `flattenEod` a t ≥ `eodFlatten` s pozíciou → zavrieť a nič ďalšie,
  3. **objem RTH** — bar 9:30 ≤ t < 16:00 pridá svoj objem do zoznamu (najviac 200),
  4. ATR ešte nie je → nič ďalšie (ani IB sa nestavia — ako v predlohe),
  5. **IB** — v okne `sessionStart` ≤ t < `sessionEnd` high / low,
  6. **vstup** — v okne `sessionEnd` ≤ t < `entryWindowEnd`, bez pozície, pokusov < `maxTradesPerDay`:
     pomer IB k priemeru posledných IB a nárast objemu → pokus sa započíta (**aj keď prieraz nie je** — predloha),
     zavretie nad IB high long / pod IB low short, market, stop a cieľ v ATR od zavretia,
  7. **záznam IB** — bary `sessionEnd` ≤ t < `sessionEnd` + 5 (HHMM) pridajú dnešný IB do priemeru
     (predloha: na 1m grafe päťkrát za deň, na 5m raz) — beží až po kroku 6, prvý bar okna vstupu ho ešte nevidí.

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

from .config import IvbConfig
from .drawing import IVB_ENTRY, IVB_ZONE

__all__ = ["IvbEngine"]

NY = ZoneInfo("America/New_York")
_LONG = "#22c55e"
_SHORT = "#ef4444"
_ZONE = "#38bdf8"


class IvbEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: IvbConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=4, atr_len=int(cfg.atrPeriod))
        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrPeriod}", self.history.atr_warmup_bars)
        self.required_history = max(1, self.warmup.chart_bars)
        self.rth_volumes: list[float] = []
        self.ib_ranges: list[float] = []
        self.day = None
        self.ib_high = float("-inf")
        self.ib_low = float("inf")
        self.ib_built = False
        self.ib_start_ms = 0
        self.todays_trades = 0
        self.boxes: list[str] = []
        self.was_in = False

    # ------------------------------------------------------------------ #

    def _close(self, out: EngineOutput, ctx: MarketContext, idx: int, reason: str) -> None:
        out.close_session = True
        for order_id in ctx.open_order_ids:
            out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason=reason))

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, long: bool, atr: float, surge: float, ib: float) -> None:
        cfg, inst = self.cfg, self.inst
        entry = bar.close
        stop = inst.round_price(entry - cfg.slAtrMult * atr if long else entry + cfg.slAtrMult * atr)
        take = inst.round_price(entry + cfg.tpAtrMult * atr if long else entry - cfg.tpAtrMult * atr)
        risk = abs(entry - stop)
        if risk < inst.tick_size:
            return
        qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, risk)
        if qty <= 0:
            return                                  # predloha: `if qty > 0`
        plan = TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=entry, stop_loss=stop,
                         take_profit=take, qty=qty, sl_distance=risk)
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"ivb:{idx}", idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.MARKET,
                                      reason=f"IVB {'long' if long else 'short'}: IB {self.ib_low:g}–{self.ib_high:g} "
                                             f"({ib:g}), objem {surge:.1f}×"))
        end = bar.time + self.step_ms
        self.boxes, self.was_in = [], False
        for kind, level, color in ((DrawKind.TP_BOX, take, _LONG), (DrawKind.SL_BOX, stop, _SHORT)):
            bid = f"ivb.{kind[:2]}.{bar.time}"
            out.drawings.append(DrawBox(kind, bar.time, max(entry, level), end, min(entry, level), color,
                                        fill_color=with_alpha(color, 60), obj_id=bid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(bid)
        out.drawings.append(DrawLabel(IVB_ENTRY, bar.time, entry, "IVB Long" if long else "IVB Short", "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"ivb.e.{bar.time}"))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        t = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        hhmm = t.hour * 100 + t.minute

        if self.boxes:
            for oid in self.boxes:
                out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
            if pos != 0.0:
                self.was_in = True
            elif self.was_in:
                self.boxes, self.was_in = [], False

        # ---- 1. nový deň ------------------------------------------------------ #
        if t.date() != self.day:
            if cfg.flattenEod and self.day is not None and pos != 0.0:
                self._close(out, ctx, idx, "nový deň — zavretie z predošlého dňa")
            self.day = t.date()
            self.ib_high, self.ib_low = float("-inf"), float("inf")
            self.ib_built = False
            self.todays_trades = 0

        ib_start, ib_end = int(cfg.sessionStart), int(cfg.sessionEnd)
        in_ib = ib_start <= hhmm < ib_end
        in_entry = ib_end <= hhmm < int(cfg.entryWindowEnd)

        # ---- 2. koniec dňa ------------------------------------------------------ #
        if cfg.flattenEod and hhmm >= int(cfg.eodFlatten) and pos != 0.0:
            self._close(out, ctx, idx, f"koniec dňa {cfg.eodFlatten:04d} NY")
            return out

        # ---- 3. objem RTH --------------------------------------------------------- #
        if 930 <= hhmm < 1600:
            self.rth_volumes.append(float(bar.volume))
            if len(self.rth_volumes) > 200:
                self.rth_volumes.pop(0)

        # ---- 4. ATR --------------------------------------------------------------- #
        atr = self.history.atr
        if atr <= 0:
            return out

        # ---- 5. IB ---------------------------------------------------------------- #
        if in_ib:
            if not self.ib_built:
                self.ib_start_ms = bar.time
            self.ib_high = max(self.ib_high, bar.high)
            self.ib_low = min(self.ib_low, bar.low)
            self.ib_built = True
            if cfg.drawIbZone:
                out.drawings.append(DrawBox(IVB_ZONE, self.ib_start_ms, self.ib_high, bar.time + self.step_ms,
                                            self.ib_low, _ZONE, fill_color=with_alpha(_ZONE, 30),
                                            obj_id=f"ivb.z.{self.ib_start_ms}", text="IVB Zone"))

        # ---- 6. vstup ------------------------------------------------------------- #
        if in_entry and self.ib_built and pos == 0.0 and self.todays_trades < int(cfg.maxTradesPerDay):
            ib = self.ib_high - self.ib_low
            n = len(self.ib_ranges)
            lb = min(int(cfg.ibRangeLookback), n)
            avg_ib = sum(self.ib_ranges[n - lb:]) / lb if lb > 0 else ib
            norm = ib / avg_ib if avg_ib > 0 else 1.0
            range_ok = cfg.minContractionRatio <= norm <= cfg.maxContractionRatio
            end = len(self.rth_volumes)
            vl = min(int(cfg.volAvgBars), end)
            avg_vol = sum(self.rth_volumes[end - vl:]) / vl if vl > 0 else 0.0
            surge = float(bar.volume) / avg_vol if avg_vol > 0 else 1.0
            if range_ok and surge >= cfg.volSurgeMult:
                self.todays_trades += 1             # predloha: pokus sa ráta aj bez prierazu
                can_long = int(cfg.direction) in (0, 1)
                can_short = int(cfg.direction) in (0, 2)
                if can_long and bar.close > self.ib_high:
                    self._enter(out, bar, idx, True, atr, surge, ib)
                elif can_short and bar.close < self.ib_low:
                    self._enter(out, bar, idx, False, atr, surge, ib)

        # ---- 7. záznam dnešného IB -------------------------------------------------- #
        if ib_end <= hhmm < ib_end + 5 and self.ib_built:
            ib = self.ib_high - self.ib_low
            if ib > 0:
                self.ib_ranges.append(ib)
                if len(self.ib_ranges) > 400:
                    self.ib_ranges.pop(0)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
