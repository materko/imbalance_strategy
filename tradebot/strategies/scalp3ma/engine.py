"""Engine Scalping 3MA + RSI + fraktál: obchod v smere trendu po potvrdení fraktálom.

Priebeh (na každom uzavretom bare grafu):

  1. tri vyhladené priemery (SMMA `ma1Len`, `ma2Len`, `ma3Len`), RSI a ATR,
  2. **trend**: zavretie pod všetkými troma priemermi = short, nad všetkými = long
     (pri `requireMaOrder` musia byť priemery aj zoradené),
  3. **RSI** pod `rsiLevel` pre short, nad ňou pre long,
  4. **fraktál** (Williams, `fractalLen` barov z každej strany) potvrdený týmto barom —
     `pullback`: short po fraktále hore, long po fraktále dole; `trend` naopak; `any` ktorýkoľvek,
  5. market na zavretí; stop pevný v bodoch, v ATR alebo za fraktál, cieľ `rrRatio` × stop,
  6. po zisku `beAtR` × riziko sa stop posunie na vstup; pri `rsiExit` sa obchod zavrie, keď RSI
     prejde cez úroveň proti nemu.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawCommand, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import FractalSide, Scalp3MaConfig, SlMode
from .drawing import S3_ENTRY, S3_FRACTAL, S3_MA

__all__ = ["Scalp3MaEngine", "BreakEven"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_MA_COLORS = ("#3b82f6", "#22c55e", "#f59e0b")
_MA_EVERY = 12   #: priemery sa kreslia ako lomená čiara s bodom každých toľko barov


@dataclass(frozen=True, slots=True)
class BreakEven(TrailingPlan):
    """Posun stopu na vstup: keď zisk dosiahne aktiváciu, stop je na cene vstupu a ďalej sa nehýbe."""

    def stop_price(self, direction: Direction, entry: float, base_stop: float, extreme: float) -> float:
        if direction is Direction.LONG:
            return max(base_stop, entry) if extreme - entry >= self.activation_price_distance else base_stop
        return min(base_stop, entry) if entry - extreme >= self.activation_price_distance else base_stop

    @classmethod
    def at(cls, distance: float, tick: float) -> "BreakEven":
        return cls(activation_price_distance=distance, offset_price_distance=0.0,
                   activation_ticks=distance / tick if tick > 0 else 0.0, offset_ticks=0.0)


class _Smma:
    """Vyhladený kĺzavý priemer (SMMA / RMA): prvá hodnota je obyčajný priemer `n` zavretí."""

    def __init__(self, n: int) -> None:
        self.n = int(n)
        self.value: float | None = None
        self._seed: list[float] = []

    def push(self, x: float) -> float | None:
        if self.value is None:
            self._seed.append(x)
            if len(self._seed) >= self.n:
                self.value = sum(self._seed) / self.n
        else:
            self.value = (self.value * (self.n - 1) + x) / self.n
        return self.value


class _Rsi:
    """RSI s Wilderovým vyhladením."""

    def __init__(self, n: int) -> None:
        self.n = int(n)
        self.prev: float | None = None
        self.up = _Smma(n)
        self.dn = _Smma(n)
        self.value: float | None = None

    def push(self, close: float) -> float | None:
        if self.prev is not None:
            d = close - self.prev
            u, v = self.up.push(max(d, 0.0)), self.dn.push(max(-d, 0.0))
            if u is not None and v is not None:
                self.value = 100.0 if v == 0 else 100.0 - 100.0 / (1.0 + u / v)
        self.prev = close
        return self.value


class Scalp3MaEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: Scalp3MaConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.mas = (_Smma(cfg.ma1Len), _Smma(cfg.ma2Len), _Smma(cfg.ma3Len))
        self.rsi = _Rsi(cfg.rsiLen)
        n = int(cfg.fractalLen)
        # SMMA sa ustáli až po niekoľkých násobkoch dĺžky — 3× najdlhší priemer
        self.warmup = Warmup(self.chart_tf_minutes).add(f"SMMA {cfg.ma3Len}", 3 * int(cfg.ma3Len)).add(
            f"RSI {cfg.rsiLen} + ATR {cfg.atrLen} + fraktál {n}", int(max(cfg.rsiLen, cfg.atrLen)) * 3 + 2 * n + 4)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=2 * n + 8 + 16, atr_len=int(cfg.atrLen))
        self._zone = ZoneInfo(cfg.tradeTZ)
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._cooldown_until = -1
        self._ma_points: list[tuple[int, float] | None] = [None, None, None]

    # ------------------------------------------------------------------ #

    def _fractal(self) -> tuple[bool, bool, Bar | None]:
        """(fraktál hore, fraktál dole, jeho bar) potvrdený týmto barom — bar `fractalLen` späť."""
        n = int(self.cfg.fractalLen)
        if not self.history.has(2 * n + 1):
            return False, False, None
        c = self.history[n]
        side = [self.history[i] for i in range(2 * n + 1) if i != n]
        return all(c.high > x.high for x in side), all(c.low < x.low for x in side), c

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        m = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= m < cfg.window_end_minutes

    def _plan(self, long: bool, entry: float, atr: float, fr: Bar) -> TradePlan | None:
        cfg = self.cfg
        if cfg.slMode is SlMode.POINTS:
            sl = cfg.slPoints.value
        elif cfg.slMode is SlMode.ATR:
            sl = cfg.slAtr.value * atr
        else:
            buf = cfg.slBufferAtr.value * atr
            sl = (entry - (fr.low - buf)) if long else ((fr.high + buf) - entry)
        if sl < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl < min_sl:
            return None
        stop = entry - sl if long else entry + sl
        take = entry + sl * cfg.rrRatio if long else entry - sl * cfg.rrRatio
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        trailing = BreakEven.at(cfg.beAtR * sl, self.inst.tick_size) if cfg.beAtR > 0 else None
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl, trailing=trailing)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index
        m1, m2, m3 = (m.push(bar.close) for m in self.mas)
        rsi = self.rsi.push(bar.close)

        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        day = (local.year, local.month, local.day)
        if day != self._day:
            self._day = day
            self._trades_today = 0

        if cfg.showMa and idx % _MA_EVERY == 0:
            for k, v in enumerate((m1, m2, m3)):
                if v is None:
                    continue
                end = bar.time + self.step_ms
                prev = self._ma_points[k]
                self._ma_points[k] = (end, v)
                if prev is not None:
                    out.drawings.append(DrawLine(S3_MA, prev[0], prev[1], end, v, _MA_COLORS[k],
                                                 obj_id=f"s3.ma{k}.{end}", text=f"SMMA {self.mas[k].n}"))

        if None in (m1, m2, m3) or rsi is None or atr <= 0:
            return out

        # ---- výstup cez RSI ------------------------------------------------ #
        if ctx.position_size != 0.0:
            if cfg.rsiExit and ((ctx.position_size > 0 and rsi < cfg.rsiLevel)
                                or (ctx.position_size < 0 and rsi > cfg.rsiLevel)):
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                                  reason=f"RSI prešlo cez {cfg.rsiLevel:g} proti obchodu"))
            return out

        up, down, fr = self._fractal()
        if not (up or down):
            return out
        top, bot = max(m1, m2, m3), min(m1, m2, m3)
        long_trend = bar.close > top and (not cfg.requireMaOrder or m1 > m2 > m3)
        short_trend = bar.close < bot and (not cfg.requireMaOrder or m1 < m2 < m3)
        side = cfg.fractalSide
        long_fr = down if side is FractalSide.PULLBACK else up if side is FractalSide.TREND else (up or down)
        short_fr = up if side is FractalSide.PULLBACK else down if side is FractalSide.TREND else (up or down)
        long = long_trend and rsi > cfg.rsiLevel and long_fr and cfg.allow_long
        short = short_trend and rsi < cfg.rsiLevel and short_fr and cfg.allow_short
        if not (long or short):
            return out
        if cfg.showFractals:
            out.drawings.append(DrawLabel(
                S3_FRACTAL, fr.time, fr.low if long else fr.high, "▲" if long else "▼",
                _LONG_COLOR if long else _SHORT_COLOR, style=LabelStyle.NONE, above=not long,
                obj_id=f"s3.fr.{fr.time}"))
        if idx < self._cooldown_until or not self._in_window(bar) or self._trades_today >= cfg.maxTradesPerDay:
            return out
        plan = self._plan(long, bar.close, atr, fr)
        if plan is None:
            return out
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"s3:{idx}", idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.MARKET,
                                      reason="trend 3 SMMA + RSI + fraktál"))
        self._trades_today += 1
        self._cooldown_until = idx + 1 + int(cfg.cooldownBars)
        out.drawings.append(DrawLabel(
            S3_ENTRY, bar.time, bar.low if long else bar.high, "LONG" if long else "SHORT", "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"s3.e.{bar.time}"))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
