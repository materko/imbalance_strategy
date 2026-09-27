"""Engine Liquidity: likvidita na viacerých TF, jej vybratie a obchod smerom k ďalšej likvidite.

Priebeh:

  1. **značenie** — na každom zapnutom TF (5m až 4h, skladá sa z barov grafu) sa z výrazných
     swingov robia úrovne likvidity (`levels.py`); rovnaké vrcholy/dná (do `liqEqualTolAtr`)
     sa zlúčia do jednej silnejšej úrovne. Úroveň žije, kým ju cena nezoberie, alebo
     `liqMaxAgeHours` — kreslí sa od swingu po miesto, kde ju cena zobrala.
  2. **spúšťač** podľa `tradeMode`:
     - ``sweep``    — cena úroveň zoberie a zavrie späť (hneď, alebo do `sweepBars`) → obchod proti
     - ``breakout`` — cena úroveň zoberie a zavrie za ňou o `breakBufferAtr` → pokračovanie
  3. **vstup** — do `setupMaxBars` barov musí prísť vstupný model v smere obchodu: IBS
     imbalance, pin bar, jeden z nich, alebo len zavretie v smere; market alebo limitka.
     Vstup len **pri likvidite**: cena vstupu najviac `entryMaxDistAtr` ATR od úrovne.
  4. **SL** podľa `slMode`, **TP** pevné RR alebo najbližšia nevybratá likvidita v smere
     (v pásme `minRR`–`maxRR`, `tpOffsetAtr` pred ňou), veľkosť z rizika.

Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawCommand, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from ..divergence.htf import TFAggregator
from .config import EntryModel, EntryOrder, LiquidityConfig, SlMode, TpMode
from .drawing import LIQ_BUY, LIQ_ENTRY, LIQ_EVENT, LIQ_SELL
from .levels import Level, SwingFinder

__all__ = ["LiquidityEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_BSL_COLOR = "#ef4444d9"
_SSL_COLOR = "#10b981d9"


@dataclass
class _Setup:
    direction: Direction
    level: float          #: úroveň, okolo ktorej udalosť vznikla
    extreme: float        #: knôt sweepu / extrém prerazovacej sviečky
    start: int
    reason: str


@dataclass
class _Watch:
    """Prerazená úroveň, pri ktorej sa ešte `sweepBars` čaká, či sa cena nevráti (neskorý sweep)."""

    level: Level
    extreme: float
    start: int


class LiquidityEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: LiquidityConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        max_age_ms = int(cfg.liqMaxAgeHours) * 3_600_000
        self.finders: list[tuple[TFAggregator, SwingFinder]] = []
        for tf in cfg.active_liq_timeframes():
            if tf < self.chart_tf_minutes or tf % self.chart_tf_minutes:
                continue   # TF menší ako graf alebo nie jeho násobok sa zo sviečok grafu poskladať nedá
            self.finders.append((TFAggregator(tf), SwingFinder(
                tf, cfg.liqPivotLen, cfg.liqMinDispAtr.value, cfg.atrLen, max_age_ms)))
        if not self.finders:
            raise ValueError(f"žiadny zapnutý TF likvidity nie je násobkom TF grafu {self.chart_tf_minutes}m")

        self.warmup = Warmup(self.chart_tf_minutes).add(
            f"ATR {cfg.atrLen} + SL okno {cfg.slLookback}", int(cfg.atrLen) + int(cfg.slLookback) + 8)
        for agg, finder in self.finders:
            bars = min(4000, 2 * int(cfg.liqPivotLen) + int(cfg.atrLen) + 5
                       + int(cfg.liqMaxAgeHours) * 60 // finder.tf)
            self.warmup.add_seeded(f"likvidita {finder.tf}m", bars, finder.tf, self._seeder(agg, finder))
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self.required_history, int(cfg.slLookback) + 4) + 16,
                                  atr_len=int(cfg.atrLen))

        self.levels: list[Level] = []
        self._uid = 0
        self._zone = ZoneInfo(cfg.tradeTZ)
        self._setup: _Setup | None = None
        self._watch: list[_Watch] = []
        self._pending: tuple[str, int] | None = None
        self._entry_bar = -1
        self._cooldown_until = -1
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._seeding = False

    # ------------------------------------------------------------------ #
    # likvidita
    # ------------------------------------------------------------------ #

    def _seeder(self, agg: TFAggregator, finder: SwingFinder):
        def seed(bars, partial: Bar | None) -> None:
            if finder.count or agg.started:
                raise RuntimeError(f"{finder.tf}m: seeding smie ísť len pred prvým barom grafu")
            self._seeding = True
            for b in bars:
                # úrovne, ktoré cena v predhistórii prerazila, sa zrušia (nekreslia sa cez cenu)
                self.levels = [lv for lv in self.levels
                               if not (lv.side == "buy" and b.high > lv.price)
                               and not (lv.side == "sell" and b.low < lv.price)
                               and b.time < lv.expires_ms]
                for lv in finder.push(b):
                    self._add_level(lv, None, finder.atr)
            self._seeding = False
            agg.prime(partial)
        return seed

    def _add_level(self, lv: Level, out: EngineOutput | None, atr_tf: float) -> None:
        """Nová úroveň; rovnaký vrchol/dno blízko existujúcej úrovne sa zlúči (equal highs/lows)."""
        tol = self.cfg.liqEqualTolAtr.value * atr_tf
        for ex in self.levels:
            if ex.side == lv.side and abs(ex.price - lv.price) <= tol:
                ex.strength += 1
                ex.price = max(ex.price, lv.price) if lv.side == "buy" else min(ex.price, lv.price)
                ex.tf = max(ex.tf, lv.tf)
                ex.expires_ms = max(ex.expires_ms, lv.expires_ms)
                return
        self._uid += 1
        lv.uid = self._uid
        self.levels.append(lv)

    def _draw_level(self, lv: Level, end_ms: int) -> DrawLine:
        buy = lv.side == "buy"
        return DrawLine(LIQ_BUY if buy else LIQ_SELL, lv.start_ms, lv.price, end_ms, lv.price,
                        _BSL_COLOR if buy else _SSL_COLOR, obj_id=f"liq.{lv.side}.{lv.start_ms}.{lv.uid}", text=lv.label)

    def _nearest(self, side: str, price: float, beyond: float = 0.0) -> Level | None:
        """Najbližšia nevybratá likvidita nad (buy) / pod (sell) cenou, aspoň `beyond` od nej."""
        best = None
        for lv in self.levels:
            if lv.side != side or lv.strength < self.cfg.liqMinStrength:
                continue
            if side == "buy" and lv.price > price + beyond and (best is None or lv.price < best.price):
                best = lv
            if side == "sell" and lv.price < price - beyond and (best is None or lv.price > best.price):
                best = lv
        return best

    # ------------------------------------------------------------------ #
    # vstupné modely
    # ------------------------------------------------------------------ #

    def _imbalance(self, long: bool, atr: float) -> bool:
        if not self.history.has(3):
            return False
        b0, b1, b2 = self.history[0], self.history[1], self.history[2]
        min_size = self.cfg.imbMinSizeAtr.value * atr
        if long:
            return b0.low > b2.high and b1.close > b2.high and (b0.low - b2.high) >= min_size
        return b0.high < b2.low and b1.close < b2.low and (b2.low - b0.high) >= min_size

    def _pinbar(self, bar: Bar, long: bool) -> bool:
        rng = bar.high - bar.low
        if rng <= 0:
            return False
        body = abs(bar.close - bar.open)
        if body > self.cfg.pbBodyPct / 100.0 * rng:
            return False
        wick = (min(bar.open, bar.close) - bar.low) if long else (bar.high - max(bar.open, bar.close))
        return wick >= self.cfg.pbWickPct / 100.0 * rng

    def _signal(self, bar: Bar, long: bool, atr: float) -> bool:
        m = self.cfg.entryModel
        if m is EntryModel.IMBALANCE:
            return self._imbalance(long, atr)
        if m is EntryModel.PINBAR:
            return self._pinbar(bar, long)
        if m is EntryModel.ANY:
            return self._imbalance(long, atr) or self._pinbar(bar, long)
        return bar.close > bar.open if long else bar.close < bar.open

    # ------------------------------------------------------------------ #
    # plán obchodu
    # ------------------------------------------------------------------ #

    def _plan(self, s: _Setup, entry: float, bar: Bar, atr: float) -> TradePlan | None:
        cfg = self.cfg
        long = s.direction is Direction.LONG
        buf = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
        mode = cfg.slMode
        if mode is SlMode.LEVEL:
            base = min(s.extreme, s.level) if long else max(s.extreme, s.level)
        elif mode is SlMode.SIGNAL:
            recent = [self.history[i] for i in range(min(3, len(self.history)))]
            base = min(b.low for b in recent) if long else max(b.high for b in recent)
        elif mode is SlMode.SWING:
            n = min(int(cfg.slLookback), len(self.history))
            recent = [self.history[i] for i in range(n)]
            base = min(b.low for b in recent) if long else max(b.high for b in recent)
        else:
            dist = cfg.slAtrMult.resolve(self.inst, price=entry, atr=atr)
            base = entry - dist if long else entry + dist
        stop = base - buf if long else base + buf
        sl = entry - stop if long else stop - entry
        if sl < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl < min_sl:
            return None
        if cfg.tpMode is TpMode.RR:
            take = entry + sl * cfg.rrRatio if long else entry - sl * cfg.rrRatio
        else:
            target = self._nearest("buy" if long else "sell", entry, beyond=sl * cfg.minRR)
            if target is None:
                return None
            off = cfg.tpOffsetAtr.resolve(self.inst, price=entry, atr=atr)
            take = target.price - off if long else target.price + off
            rr = abs(take - entry) / sl
            if rr < cfg.minRR or (cfg.maxRR > 0 and rr > cfg.maxRR):
                return None
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=s.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    # ------------------------------------------------------------------ #

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        m = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= m < cfg.window_end_minutes

    def _event_label(self, out: EngineOutput, bar: Bar, text: str, above: bool, long: bool) -> None:
        if self.cfg.showEvents:
            out.drawings.append(DrawLabel(
                LIQ_EVENT, bar.time, bar.high if above else bar.low, text, "#ffffff",
                style=LabelStyle.NONE, above=above, bg_color=_LONG_COLOR if long else _SHORT_COLOR,
                obj_id=f"liqev.{bar.time}.{text}"))

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg

        # vyššie TF: uzavreté bary → nové úrovne (pred rozhodovaním o tomto bare)
        for agg, finder in self.finders:
            closed = agg.push(bar)
            if closed is not None:
                for lv in finder.push(closed):
                    self._add_level(lv, out, finder.atr)

        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        day = (local.year, local.month, local.day)
        if day != self._day:
            self._day = day
            self._trades_today = 0

        # ---- vybratie likvidity a vypršanie -------------------------------- #
        buffer = cfg.breakBufferAtr.resolve(self.inst, price=bar.close, atr=atr) if atr > 0 else 0.0
        taken: list[tuple[Level, str]] = []
        keep: list[Level] = []
        for lv in self.levels:
            # vybratie = cena úroveň prerazí; presný dotyk je rovnaký vrchol/dno (equal highs/lows),
            # ktorý sa zlúči do silnejšej úrovne, nie jej vyplnenie
            if lv.side == "buy" and bar.high > lv.price:
                taken.append((lv, "buy"))
            elif lv.side == "sell" and bar.low < lv.price:
                taken.append((lv, "sell"))
            elif bar.time >= lv.expires_ms:
                if cfg.showLevels:
                    out.drawings.append(self._draw_level(lv, lv.expires_ms))
            else:
                keep.append(lv)
        self.levels = keep
        events: list[tuple[Direction, Level, float, str]] = []
        for lv, side in taken:
            if cfg.showLevels:
                out.drawings.append(self._draw_level(lv, bar.time))   # končí na sviečke, ktorá ju prerazila
            if lv.strength < cfg.liqMinStrength:
                continue
            buy = side == "buy"
            back = bar.close < lv.price if buy else bar.close > lv.price
            beyond = bar.close > lv.price + buffer if buy else bar.close < lv.price - buffer
            if back:
                events.append((Direction.SHORT if buy else Direction.LONG, lv,
                               bar.high if buy else bar.low, "sweep"))
            elif beyond:
                events.append((Direction.LONG if buy else Direction.SHORT, lv,
                               bar.low if buy else bar.high, "breakout"))
                self._watch.append(_Watch(lv, bar.high if buy else bar.low, idx))
        # neskorý sweep: prerazená úroveň, pod/nad ktorú cena do `sweepBars` zavrie späť
        still: list[_Watch] = []
        for w in self._watch:
            if w.start == idx:
                still.append(w)
                continue
            buy = w.level.side == "buy"
            w.extreme = max(w.extreme, bar.high) if buy else min(w.extreme, bar.low)
            back = bar.close < w.level.price if buy else bar.close > w.level.price
            if back:
                events.append((Direction.SHORT if buy else Direction.LONG, w.level, w.extreme, "sweep"))
            elif idx - w.start < cfg.sweepBars:
                still.append(w)
        self._watch = still

        # ---- nevyplnená limitka, pozícia, časový limit --------------------- #
        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 1:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="nevyplnené"))
            self._pending = None
        if ctx.position_size != 0.0:
            self._pending = None
            self._setup = None
        elif self._entry_bar >= 0 and self._pending is None:
            self._entry_bar = -1
        if (cfg.maxHoldBars > 0 and ctx.position_size != 0.0 and self._entry_bar >= 0
                and idx - self._entry_bar >= cfg.maxHoldBars):
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                              reason=f"drží sa dlhšie než {cfg.maxHoldBars} barov"))
            self._entry_bar = -1
        if ctx.position_size != 0.0 or self._pending is not None or atr <= 0:
            return out

        # ---- nový setup z udalosti ----------------------------------------- #
        mode = cfg.tradeMode
        for direction, lv, extreme, kind in events:
            if kind != mode.value:
                continue
            long = direction is Direction.LONG
            self._event_label(out, bar, "sweep" if kind == "sweep" else "prerazenie",
                              above=lv.side == "buy", long=long)
            if (long and not cfg.allow_long) or (not long and not cfg.allow_short):
                continue
            self._setup = _Setup(direction, lv.price, extreme, idx, kind)
            break

        if idx < self._cooldown_until:
            return out
        in_window = self._in_window(bar)
        if not in_window or self._trades_today >= cfg.maxTradesPerDay:
            return out

        # ---- vstup v rámci setupu ------------------------------------------ #
        s = self._setup
        if s is None:
            return out
        long = s.direction is Direction.LONG
        if idx - s.start > cfg.setupMaxBars:
            self._setup = None
            return out
        # zneplatnenie: sweep — cena ide za knôt; prerazenie — cena zavrie späť za úroveň
        if s.reason == "sweep":
            if (long and bar.low < s.extreme) or (not long and bar.high > s.extreme):
                self._setup = None
                return out
        elif (long and bar.close < s.level - buffer) or (not long and bar.close > s.level + buffer):
            self._setup = None
            return out
        if not self._signal(bar, long, atr):
            return out
        # vstup len pri likvidite: cena vstupu smie byť od úrovne najviac `entryMaxDistAtr` ATR,
        # inak by signál prišiel ďaleko od zóny (a stop za knôtom sweepu by bol obrovský)
        entry = (bar.high + bar.low) / 2.0 if cfg.entryOrder is EntryOrder.LIMIT else bar.close
        if abs(entry - s.level) > cfg.entryMaxDistAtr.resolve(self.inst, price=entry, atr=atr):
            return out
        self._enter(out, s, bar, atr, idx)
        return out

    def _enter(self, out: EngineOutput, s: _Setup, bar: Bar, atr: float, idx: int) -> None:
        cfg = self.cfg
        limit = cfg.entryOrder is EntryOrder.LIMIT
        entry = (bar.high + bar.low) / 2.0 if limit else bar.close
        plan = self._plan(s, entry, bar, atr)
        self._setup = None
        self._cooldown_until = idx + int(cfg.cooldownBars)
        if plan is None:
            return
        order_id = f"liq:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=s.direction, plan=plan,
                                      order_type=OrderType.LIMIT if limit else OrderType.MARKET,
                                      reason=f"{s.reason} + {cfg.entryModel.value}"))
        self._pending = (order_id, idx)
        self._entry_bar = idx
        self._trades_today += 1
        long = s.direction is Direction.LONG
        out.drawings.append(DrawLabel(
            LIQ_ENTRY, bar.time, bar.low if long else bar.high, f"{'LONG' if long else 'SHORT'} {s.reason}",
            "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"liqe.{bar.time}"))

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        """Nevybratá likvidita na konci dát — po posledný bar (šípka „ešte čaká“)."""
        if not self.cfg.showLevels:
            return []
        end = bar.time + self.step_ms
        return [self._draw_level(lv, end) for lv in self.levels]
