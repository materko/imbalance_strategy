"""Engine SWEEPING ENGULF 1.0: sviečka vyberie extrém predošlej a zavrie za jej opačný koniec → market.

Na každom uzavretom bare grafu (video: 4h) sa porovná so sviečkou pred ním:

* **long** — low pod low predošlej (výber), zavretie nad jej high (`engulfMode` body: nad jej telom),
* **short** — high nad high predošlej, zavretie pod jej low (telom),
* predošlá sviečka podľa `prevCandle` (video: smerom manipulácie, teda proti obchodu).

Vstup market na zavretí; stop za extrém signálnej sviečky alebo `atrMult` × ATR, cieľ `rrRatio` × stop. Kým beží
obchod, nové signály sa neberú. Filter trendu EMA, typ príkazu a potvrdenie sú spoločné obaly jadra.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from tradebot.core.drawing import DrawCommand, DrawLabel, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import EngulfMode, PrevCandle, SlMethod, SweepEngulfConfig
from .drawing import SE_SIGNAL

__all__ = ["SweepEngulfEngine"]

LONG_COLOR, SHORT_COLOR = "#10b981", "#ef4444"


class SweepEngulfEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: SweepEngulfConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        self.warmup = Warmup(self.tf).add(f"ATR {cfg.atrLen}", int(cfg.atrLen) * 3 + 2)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=self.required_history + 8, atr_len=int(cfg.atrLen))

    def signal(self) -> Direction | None:
        """Smer obchodu, ak práve uzavretá sviečka vybrala extrém predošlej a pohltila ju."""
        if not self.history.has(2):
            return None
        cfg = self.cfg
        cur, prev = self.history[0], self.history[1]
        body = cfg.engulfMode is EngulfMode.BODY
        up_edge = max(prev.open, prev.close) if body else prev.high
        dn_edge = min(prev.open, prev.close) if body else prev.low
        prev_bull, prev_bear = prev.close > prev.open, prev.close < prev.open
        if cur.low < prev.low and cur.close > up_edge:
            d = Direction.LONG
            ok = {PrevCandle.OPPOSITE: prev_bear, PrevCandle.SAME: prev_bull}.get(cfg.prevCandle, True)
        elif cur.high > prev.high and cur.close < dn_edge:
            d = Direction.SHORT
            ok = {PrevCandle.OPPOSITE: prev_bull, PrevCandle.SAME: prev_bear}.get(cfg.prevCandle, True)
        else:
            return None
        return d if ok else None

    def _plan(self, d: Direction, bar: Bar, atr: float) -> TradePlan | None:
        cfg = self.cfg
        long = d is Direction.LONG
        entry = bar.close
        if cfg.slMethod is SlMethod.ATR:
            if atr <= 0:
                return None
            sl = cfg.atrMult * atr
            stop = entry - sl if long else entry + sl
        else:
            buf = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr) if atr > 0 else 0.0
            stop = bar.low - buf if long else bar.high + buf
            sl = abs(entry - stop)
        if sl < self.inst.tick_size * 2:
            return None
        take = entry + cfg.rrRatio * sl if long else entry - cfg.rrRatio * sl
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        return TradePlan(direction=d, entry=self.inst.round_price(entry), stop_loss=self.inst.round_price(stop),
                         take_profit=self.inst.round_price(take), qty=qty if qty > 0 else 1.0, sl_distance=sl)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        cfg, out = self.cfg, EngineOutput()
        self.history.append(bar)
        idx = self.history.bar_index
        if ctx.position_size != 0.0:
            return out                                  # kým beží obchod, nové signály sa neberú
        d = self.signal()
        if d is None:
            return out
        long = d is Direction.LONG
        if (long and not cfg.allow_long) or (not long and not cfg.allow_short):
            return out
        plan = self._plan(d, bar, self.history.atr)
        if plan is None:
            return out
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"se:{idx}", idx, direction=d, plan=plan,
                                      order_type=OrderType.MARKET, reason="výber + pohltenie predošlej sviečky"))
        if cfg.showSignals:
            out.drawings.append(DrawLabel(SE_SIGNAL, bar.time, bar.low if long else bar.high,
                                          "SE ▲" if long else "SE ▼", "#ffffff",
                                          style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                          bg_color=LONG_COLOR if long else SHORT_COLOR, obj_id=f"se.{bar.time}"))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
