"""Engine stratégie FVG POLARITY: market obchod späť k práve vzniknutému FVG, TP na jeho dotyk.

Na každom uzavretom bare grafu (zadanie: 15m) sa pozrie na posledné tri sviečky:

* **medvedí FVG** — low 1. sviečky je nad high 3. sviečky; medzera je ``[high3, low1]`` nad
  cenou → **long** k nej
* **býčí FVG** — high 1. sviečky je pod low 3. sviečky; medzera ``[high1, low3]`` pod cenou →
  **short** k nej

FVG je potvrdený zavretím 3. sviečky; vstup je market na tom zavretí, takže sa vyplní na
otvorení najbližšej sviečky. Cieľ je dotyk medzery (``tpLevel``: bližšia hrana, stred alebo
vzdialená hrana), stop ``slPoints`` bodov od vstupu. Obchod sa drží, kým nepríde TP alebo SL;
kým beží, ďalšie FVG sa neobchodujú.

Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from tradebot.core.drawing import DrawBox, DrawCommand, DrawLabel, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import FvgPolarityConfig, TpLevel
from .drawing import FP_ENTRY, FP_FVG

__all__ = ["FvgPolarityEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_BEAR_FVG = "#be185d33"
_BULL_FVG = "#3b82f633"
#: ako ďaleko doprava sa kreslí box FVG (v baroch grafu)
_BOX_BARS = 20


class FvgPolarityEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: FvgPolarityConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        #: predhistória: tri sviečky na FVG a ATR (len kvôli jednotke `atr`, keby ju niekto zvolil)
        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrLen}", int(cfg.atrLen) + 3)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=self.required_history + 8, atr_len=int(cfg.atrLen))

    # ------------------------------------------------------------------ #

    def find_fvg(self) -> tuple[Direction, float, float] | None:
        """Práve potvrdený FVG: (smer obchodu k nemu, spodok medzery, vrch medzery)."""
        if not self.history.has(2):
            return None
        c1, c3 = self.history[2], self.history[0]
        if c1.low > c3.high:      # medvedí FVG nad cenou -> long k nemu
            return Direction.LONG, c3.high, c1.low
        if c1.high < c3.low:      # býčí FVG pod cenou -> short k nemu
            return Direction.SHORT, c1.high, c3.low
        return None

    def _size_ok(self, size: float, price: float, atr: float) -> bool:
        lo = self.cfg.fvgMinSize.resolve(self.inst, price=price, atr=atr)
        hi = self.cfg.fvgMaxSize.resolve(self.inst, price=price, atr=atr)
        return size >= lo and (hi <= 0 or size <= hi)

    def _target(self, direction: Direction, bottom: float, top: float) -> float:
        level = self.cfg.tpLevel
        if level is TpLevel.MID:
            return (bottom + top) / 2.0
        long = direction is Direction.LONG
        if level is TpLevel.FAR:
            return top if long else bottom
        return bottom if long else top           # NEAR: prvý dotyk medzery

    def _plan(self, direction: Direction, entry: float, take: float, atr: float) -> TradePlan | None:
        cfg = self.cfg
        long = direction is Direction.LONG
        sl_distance = cfg.slPoints.resolve(self.inst, price=entry, atr=atr)
        if sl_distance < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl_distance < min_sl:
            return None
        if (take - entry if long else entry - take) < self.inst.tick_size * 2:
            return None  # cena už pri medzere — nie je čo zobrať
        stop = entry - sl_distance if long else entry + sl_distance
        qty = (cfg.position_qty(self.inst, cfg.riskDollar, sl_distance)
               if cfg.riskDollar > 0 else 1.0)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(
            direction=direction, entry=self.inst.round_price(entry),
            stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
            qty=qty, sl_distance=sl_distance,
        )

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        fvg = self.find_fvg()
        if fvg is None:
            return out
        direction, bottom, top = fvg
        if not self._size_ok(top - bottom, bar.close, atr):
            return out
        long = direction is Direction.LONG
        if cfg.showFvg:
            start = self.history[2].time
            out.drawings.append(DrawBox(
                FP_FVG, start, top, bar.time + self.step_ms * _BOX_BARS, bottom,
                _BEAR_FVG if long else _BULL_FVG, obj_id=f"fp_fvg.{bar.time}",
                text=f"FVG {top - bottom:.2f}",
            ))
        if ctx.position_size != 0.0:
            return out
        if (long and not cfg.allow_long) or (not long and not cfg.allow_short):
            return out
        plan = self._plan(direction, bar.close, self._target(direction, bottom, top), atr)
        if plan is None:
            return out
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"fp:{idx}", idx, direction=direction,
                                      plan=plan, order_type=OrderType.MARKET,
                                      reason="FVG potvrdený — market k medzere"))
        out.drawings.append(DrawLabel(
            FP_ENTRY, bar.time, bar.low if long else bar.high, "LONG" if long else "SHORT", "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"fp_entry.{bar.time}",
        ))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
