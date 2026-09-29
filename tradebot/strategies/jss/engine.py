"""Engine JSS 1.0: BOS / CHoCH na TF štruktúry → SD zóna, ktorá ho spôsobila → vstup v zóne.

Priebeh:

  1. **štruktúra** — z barov grafu sa skladá TF štruktúry (`structTF`). Swing je pivot so
     `swingLen` barmi z oboch strán; použije sa až po potvrdení (bez pohľadu dopredu).
     Sviečka, ktorá **zavrie** za posledným swingom, je BOS (v smere trendu) alebo CHoCH
     (proti nemu, trend sa otočí). Prerazený swing je spotrebovaný.
  2. **zóna** — noha, ktorá swing prerazila, začína na extréme medzi prerazeným swingom
     a sviečkou prerazenia (pri býčom BOS najnižšie dno). Od neho sa hľadá prvá impulzná
     sviečka v smere (telo aspoň `impulseAtr` ATR); zóna je posledná opačná sviečka pred ňou
     (`ob`) alebo báza pred ňou (`base`). Nový BOS nahradí zónu starého.
  3. **vstup** — len pri prvom návrate do zóny: limitka na hranu (`touch`, `entryDepthPct`
     do hĺbky), alebo po dotyku IBS imbalance / pin bar na grafe do `confirmBars` barov.
     Zóna končí dotykom (potom sa už neobchoduje), zavretím za protiľahlou hranou alebo vekom.
  4. **SL** za protiľahlou hranou zóny (+ `slBufferAtr`), **TP** RR alebo extrém nohy BOS.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawLabel, DrawLine, LabelStyle, LineStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import EntryModel, JssConfig, TpMode, TriggerMode, ZoneEdge, ZoneType
from .drawing import JSS_BOS, JSS_CHOCH, JSS_ENTRY, JSS_ZONE

__all__ = ["JssEngine", "StructAggregator"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_DEMAND_FILL = "#10b98133"
_SUPPLY_FILL = "#3b82f633"
_BOS_COLOR = "#94a3b8"
_CHOCH_COLOR = "#f59e0b"


class StructAggregator:
    """Bary TF štruktúry z barov grafu. Bar sa uzavrie hneď na poslednom bare grafu svojej
    periódy (nie až s prvým barom ďalšej) — pri TF štruktúry = TF grafu je to ten istý bar."""

    def __init__(self, minutes: int, chart_minutes: int) -> None:
        self.ms = int(minutes) * 60_000
        self.step = int(chart_minutes) * 60_000
        self._p: int | None = None
        self._o = self._h = self._l = self._c = self._v = 0.0

    @property
    def started(self) -> bool:
        return self._p is not None

    def _emit(self) -> Bar:
        b = Bar(time=self._p, open=self._o, high=self._h, low=self._l, close=self._c, volume=self._v)
        self._p = None
        return b

    def push(self, bar: Bar) -> list[Bar]:
        out: list[Bar] = []
        period = bar.time // self.ms * self.ms
        if self._p is not None and period != self._p:   # medzera v dátach — perióda skončila bez posledného baru
            out.append(self._emit())
        if self._p is None:
            self._p = period
            self._o, self._h, self._l, self._c, self._v = bar.open, bar.high, bar.low, bar.close, bar.volume
        else:
            self._h = max(self._h, bar.high)
            self._l = min(self._l, bar.low)
            self._c = bar.close
            self._v += bar.volume
        if bar.time + self.step >= period + self.ms:
            out.append(self._emit())
        return out

    def prime(self, partial: Bar | None) -> None:
        if partial is None:
            return
        self._p = partial.time // self.ms * self.ms
        self._o, self._h, self._l = partial.open, partial.high, partial.low
        self._c, self._v = partial.close, partial.volume


@dataclass
class _Swing:
    price: float
    idx: int      #: index baru štruktúry
    time: int


@dataclass
class _Zone:
    direction: Direction
    top: float
    bot: float
    start_ms: int     #: čas prvej sviečky zóny — odtiaľ sa kreslí
    born_idx: int     #: index baru štruktúry, na ktorom vznikla (BOS)
    target: float     #: extrém nohy BOS (cieľ pri tpMode=structure)
    uid: int
    touched_idx: int = -1   #: index baru grafu prvého dotyku

    @property
    def near(self) -> float:
        """Hrana, na ktorú cena príde prvá (supply: spodná, demand: horná)."""
        return self.bot if self.direction is Direction.SHORT else self.top

    def near_at(self, depth_pct: float) -> float:
        """Cena vstupu `depth_pct` % do hĺbky zóny od bližšej hrany."""
        h = (self.top - self.bot) * depth_pct / 100.0
        return self.bot + h if self.direction is Direction.SHORT else self.top - h

    @property
    def far(self) -> float:
        """Protiľahlá hrana — za ňou je stop (supply: horná, demand: spodná)."""
        return self.top if self.direction is Direction.SHORT else self.bot


class JssEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: JssConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        tf = int(cfg.structTF)
        if tf < self.chart_tf_minutes or tf % self.chart_tf_minutes:
            # z barov grafu sa dá poskladať len násobok TF grafu — najbližší vyšší (5m na 3m grafe = 6m)
            tf = -(-max(tf, self.chart_tf_minutes) // self.chart_tf_minutes) * self.chart_tf_minutes
        self.struct_tf = tf
        self.agg = StructAggregator(tf, self.chart_tf_minutes)
        n = int(cfg.swingLen)
        self.sbars: deque[Bar] = deque(maxlen=max(400, 2 * n + 10))
        self.s_idx = -1
        self.s_atr = 0.0
        self._s_seed: list[float] = []
        self.sh: _Swing | None = None   #: posledný potvrdený swing high (nespotrebovaný)
        self.sl: _Swing | None = None
        self.sh_any: _Swing | None = None   #: posledný swing high aj spotrebovaný (začiatok nohy)
        self.sl_any: _Swing | None = None
        self.trend = 0
        self.zone: _Zone | None = None
        self._uid = 0
        self._seeding = False

        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrLen}", int(cfg.atrLen) + 8)
        self.warmup.add_seeded(f"štruktúra {tf}m", 2 * n + int(cfg.atrLen) + 60, tf, self._seed)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self.required_history, 8) + 16, atr_len=int(cfg.atrLen))

        self._zone_tz = ZoneInfo(cfg.tradeTZ)
        self._pending: tuple[str, int] | None = None
        self._entry_bar = -1
        self._cooldown_until = -1
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0

    # ------------------------------------------------------------------ #
    # štruktúra
    # ------------------------------------------------------------------ #

    def _seed(self, bars, partial: Bar | None) -> None:
        if self.s_idx >= 0 or self.agg.started:
            raise RuntimeError("seeding smie ísť len pred prvým barom grafu")
        self._seeding = True
        for b in bars:
            self._on_struct(b, None)
        self._seeding = False
        self.agg.prime(partial)

    def _update_atr(self, b: Bar) -> None:
        prev = self.sbars[-1] if self.sbars else None
        tr = b.high - b.low if prev is None else max(b.high - b.low, abs(b.high - prev.close), abs(b.low - prev.close))
        if self.s_atr > 0:
            self.s_atr += (tr - self.s_atr) / int(self.cfg.atrLen)
        else:
            self._s_seed.append(tr)
            if len(self._s_seed) >= int(self.cfg.atrLen):
                self.s_atr = sum(self._s_seed) / len(self._s_seed)

    def _sbar(self, idx: int) -> Bar | None:
        """Bar štruktúry s indexom `idx` (ak je ešte v okne)."""
        k = idx - (self.s_idx - len(self.sbars) + 1)
        return self.sbars[k] if 0 <= k < len(self.sbars) else None

    def _on_struct(self, b: Bar, out: EngineOutput | None) -> None:
        cfg = self.cfg
        self._update_atr(b)
        self.sbars.append(b)
        self.s_idx += 1
        n = int(cfg.swingLen)
        # potvrdený pivot na bare s `n` barmi vpravo
        if len(self.sbars) >= 2 * n + 1:
            c = self.sbars[-n - 1]
            left = [self.sbars[-n - 1 - k] for k in range(1, n + 1)]
            right = [self.sbars[-k] for k in range(1, n + 1)]
            ci = self.s_idx - n
            if all(c.high > x.high for x in left) and all(c.high > x.high for x in right):
                self.sh = self.sh_any = _Swing(c.high, ci, c.time)
            if all(c.low < x.low for x in left) and all(c.low < x.low for x in right):
                self.sl = self.sl_any = _Swing(c.low, ci, c.time)
        # BOS / CHoCH — rozhoduje zavretie
        if self.sh is not None and b.close > self.sh.price:
            self._event(Direction.LONG, self.sh, b, out)
            self.sh = None
        elif self.sl is not None and b.close < self.sl.price:
            self._event(Direction.SHORT, self.sl, b, out)
            self.sl = None

    def _event(self, d: Direction, sw: _Swing, b: Bar, out: EngineOutput | None) -> None:
        cfg = self.cfg
        up = d is Direction.LONG
        kind = "BOS" if self.trend == (1 if up else -1) else "CHoCH"
        self.trend = 1 if up else -1
        if out is not None and cfg.showStructure:
            out.drawings.append(DrawLine(JSS_BOS if kind == "BOS" else JSS_CHOCH, sw.time, sw.price, b.time, sw.price,
                                         _BOS_COLOR if kind == "BOS" else _CHOCH_COLOR, style=LineStyle.DASHED,
                                         obj_id=f"jss.{kind}.{sw.time}", text=kind))
        if self._seeding:
            return
        tm = cfg.triggerMode
        if (tm is TriggerMode.BOS and kind != "BOS") or (tm is TriggerMode.CHOCH and kind != "CHoCH"):
            return
        zone = self._find_zone(d, sw, b)
        if zone is None:
            return
        if self.zone is not None and out is not None:
            self._draw_zone(out, self.zone, b.time)   # nový BOS nahradí starú zónu
        self.zone = zone

    def _find_zone(self, d: Direction, sw: _Swing, b: Bar) -> _Zone | None:
        """SD zóna na začiatku nohy, ktorá swing `sw` prerazila."""
        cfg = self.cfg
        atr = self.s_atr
        if atr <= 0:
            return None
        up = d is Direction.LONG
        first = max(sw.idx, self.s_idx - len(self.sbars) + 1)
        seg = [(i, self._sbar(i)) for i in range(first, self.s_idx + 1)]
        seg = [(i, x) for i, x in seg if x is not None]
        if len(seg) < 2:
            return None
        # začiatok nohy: extrém proti smeru medzi prerazeným swingom a prerazením
        o_i, o_bar = (min(seg, key=lambda t: t[1].low) if up else max(seg, key=lambda t: t[1].high))
        leg = [(i, x) for i, x in seg if i >= o_i]
        imp_min = cfg.impulseAtr.value * atr
        j = None
        for i, x in leg:
            body = x.close - x.open
            if (body if up else -body) >= imp_min:
                j = i
                break
        if j is None:
            return None
        before = [(i, x) for i, x in leg if i < j] or [(o_i, o_bar)]
        opposite = (lambda x: x.close < x.open) if up else (lambda x: x.close > x.open)
        if cfg.zoneType is ZoneType.OB:
            cand = [t for t in before if opposite(t[1])]
            zb = [cand[-1] if cand else before[-1]]
        else:
            zb = before[-int(cfg.baseMaxBars):]
        hi = max(x.high for _, x in zb)
        lo = min(x.low for _, x in zb)
        if cfg.zoneEdge is ZoneEdge.BODY:   # bližšia hrana na tele sviečok zóny
            if up:
                hi = max(max(x.open, x.close) for _, x in zb)
            else:
                lo = min(min(x.open, x.close) for _, x in zb)
        h = hi - lo
        if h <= 0 or h < cfg.zoneMinAtr.value * atr or (cfg.zoneMaxAtr.value > 0 and h > cfg.zoneMaxAtr.value * atr):
            return None
        # zóna musí byť za cenou (návrat do nej je pullback), nie pod ňou / nad ňou
        if (up and b.close <= hi) or (not up and b.close >= lo):
            return None
        leg_ext = max(x.high for _, x in leg) if up else min(x.low for _, x in leg)
        self._uid += 1
        return _Zone(d, hi, lo, zb[0][1].time, self.s_idx, leg_ext, self._uid)

    def _draw_zone(self, out: EngineOutput, z: _Zone, end_ms: int) -> None:
        if not self.cfg.showZones:
            return
        long = z.direction is Direction.LONG
        out.drawings.append(DrawBox(JSS_ZONE, z.start_ms, z.top, max(end_ms, z.start_ms), z.bot,
                                    _LONG_COLOR if long else "#3b82f6", _DEMAND_FILL if long else _SUPPLY_FILL,
                                    obj_id=f"jss.zone.{z.uid}", text="demand" if long else "supply"))

    # ------------------------------------------------------------------ #
    # vstupné modely (na baroch grafu)
    # ------------------------------------------------------------------ #

    def _imbalance(self, long: bool, atr: float) -> bool:
        if not self.history.has(3):
            return False
        b0, b1, b2 = self.history[0], self.history[1], self.history[2]
        m = self.cfg.imbMinSizeAtr.value * atr
        if long:
            return b0.low > b2.high and b1.close > b2.high and (b0.low - b2.high) >= m
        return b0.high < b2.low and b1.close < b2.low and (b2.low - b0.high) >= m

    def _pinbar(self, bar: Bar, long: bool) -> bool:
        rng = bar.high - bar.low
        if rng <= 0 or abs(bar.close - bar.open) > self.cfg.pbBodyPct / 100.0 * rng:
            return False
        wick = (min(bar.open, bar.close) - bar.low) if long else (bar.high - max(bar.open, bar.close))
        return wick >= self.cfg.pbWickPct / 100.0 * rng

    def _signal(self, bar: Bar, long: bool, atr: float) -> bool:
        m = self.cfg.entryModel
        if m is EntryModel.IMBALANCE:
            return self._imbalance(long, atr)
        if m is EntryModel.PINBAR:
            return self._pinbar(bar, long)
        return self._imbalance(long, atr) or self._pinbar(bar, long)

    # ------------------------------------------------------------------ #

    def _plan(self, z: _Zone, entry: float, atr: float) -> TradePlan | None:
        cfg = self.cfg
        long = z.direction is Direction.LONG
        buf = (cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
               + cfg.slBufferPoints.resolve(self.inst, price=entry, atr=atr))
        stop = z.far - buf if long else z.far + buf
        sl = entry - stop if long else stop - entry
        if sl < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl < min_sl:
            return None
        if cfg.tpMode is TpMode.RR:
            take = entry + sl * cfg.rrRatio if long else entry - sl * cfg.rrRatio
        else:
            take = z.target
            if (take - entry if long else entry - take) < sl * cfg.minRR:
                return None
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=z.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone_tz)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        m = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= m < cfg.window_end_minutes

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone_tz)
        day = (local.year, local.month, local.day)
        if day != self._day:
            self._day = day
            self._trades_today = 0

        # ---- zóna: dotyk, zneplatnenie, vek (na tomto bare, pred novou štruktúrou) ---- #
        z = self.zone
        if z is not None:
            short = z.direction is Direction.SHORT
            if z.touched_idx < 0 and ((short and bar.high >= z.near_at(cfg.entryDepthPct))
                                      or (not short and bar.low <= z.near_at(cfg.entryDepthPct))):
                z.touched_idx = idx
            beyond = bar.close > z.top if short else bar.close < z.bot
            old = cfg.zoneMaxAgeBars > 0 and self.s_idx - z.born_idx > cfg.zoneMaxAgeBars
            done = z.touched_idx >= 0 and (cfg.entryModel is EntryModel.TOUCH
                                           or idx - z.touched_idx >= int(cfg.confirmBars))
            if beyond or old or done:
                self._draw_zone(out, z, bar.time)
                self.zone = None

        # ---- nevyplnená limitka, pozícia, časový limit ---------------------- #
        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 1:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1], reason="nevyplnené"))
            self._pending = None
        if ctx.position_size != 0.0:
            if self._pending is not None and self._pending[0].startswith("jssL:"):   # limitka sa vyplnila
                self._trades_today += 1
                self._cooldown_until = idx + int(cfg.cooldownBars)
            self._pending = None
        elif self._entry_bar >= 0 and self._pending is None:
            self._entry_bar = -1
        if (cfg.maxHoldBars > 0 and ctx.position_size != 0.0 and self._entry_bar >= 0
                and idx - self._entry_bar >= cfg.maxHoldBars):
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                              reason=f"drží sa dlhšie než {cfg.maxHoldBars} barov"))
            self._entry_bar = -1

        # ---- štruktúra: uzavreté bary TF štruktúry (po zavretí tohto baru) --- #
        for sb in self.agg.push(bar):
            self._on_struct(sb, out)

        z = self.zone
        if z is None or ctx.position_size != 0.0 or self._pending is not None or atr <= 0:
            return out
        long = z.direction is Direction.LONG
        if (long and not cfg.allow_long) or (not long and not cfg.allow_short):
            return out
        if idx < self._cooldown_until or not self._in_window(bar) or self._trades_today >= cfg.maxTradesPerDay:
            return out

        if cfg.entryModel is EntryModel.TOUCH:
            # limitka na hranu zóny platí na ďalší bar; kým zóna žije a nie je dotknutá, obnovuje sa
            if z.touched_idx < 0:
                price = z.near_at(cfg.entryDepthPct)
                if (long and bar.close > price) or (not long and bar.close < price):
                    self._enter(out, z, price, bar, atr, idx, limit=True)
            return out
        # imbalance / pin bar po dotyku, vstup na zavretí — cena musí byť ešte pred protiľahlou hranou
        if z.touched_idx >= 0 and self._signal(bar, long, atr):
            if (long and bar.close > z.far) or (not long and bar.close < z.far):
                self._enter(out, z, bar.close, bar, atr, idx, limit=False)
                if self.zone is z and self._pending is not None:
                    self._draw_zone(out, z, bar.time)
                    self.zone = None
        return out

    def _enter(self, out: EngineOutput, z: _Zone, entry: float, bar: Bar, atr: float, idx: int, limit: bool) -> None:
        cfg = self.cfg
        plan = self._plan(z, entry, atr)
        if plan is None:
            return
        order_id = f"{'jssL' if limit else 'jss'}:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=z.direction, plan=plan,
                                      order_type=OrderType.LIMIT if limit else OrderType.MARKET,
                                      reason=f"{'BOS zóna' if limit else cfg.entryModel.value} {z.uid}"))
        self._pending = (order_id, idx)
        self._entry_bar = idx
        if not limit:
            self._trades_today += 1
            self._cooldown_until = idx + int(cfg.cooldownBars)
            long = z.direction is Direction.LONG
            out.drawings.append(DrawLabel(
                JSS_ENTRY, bar.time, bar.low if long else bar.high, f"{'LONG' if long else 'SHORT'} {cfg.entryModel.value}",
                "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"jsse.{bar.time}"))

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        if self.zone is None or not self.cfg.showZones:
            return []
        out = EngineOutput()
        self._draw_zone(out, self.zone, bar.time + self.step_ms)
        return list(out.drawings)
