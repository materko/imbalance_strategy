"""Engine ASIA SWEEP 1.0 — vybratie likvidity Ázie v londýnskej seanse a vstup do protismeru.

Priebeh (na každom uzavretom bare grafu, čas New York podľa otvorenia baru; „cyklus" začína
začiatkom rangu Ázie, takže okná cez polnoc idú za sebou):

  1. **range Ázie**: maximum a minimum sviečok v okne `asiaStart`–`asiaEnd`; nový cyklus zruší staré
     setupy; range, ktorý beh zastihol v polovici, sa neobchoduje; voliteľný filter veľkosti rangu,
  2. **sweep**: v okne `sweepStart`–`sweepEnd` cena prerazí maximum (minimum) Ázie aspoň o `sweepMin`;
     extrém sweepu sa ďalej sleduje, hlbší než `maxSweep` setup ruší; pri `requireReclaim` musí
     sviečka zavrieť späť v range,
  3. **vstup** do protismeru (maximum vybraté → short, minimum → long) najneskôr `entryBars` sviečok
     po sweepe a pred `entryEnd`: vstupný model (IBS imbalance / pin bar / ktorýkoľvek / zavretie
     v smere) na zavretí sviečky, market; jedna pozícia naraz, najviac `maxTradesPerDay` za cyklus,
  4. **stop** za extrémom sweepu / signálnej sviečky (+ `slBuffer`) alebo `slAtr`; **cieľ** RR,
     opačná strana rangu, jeho stred alebo najbližší naked POC; pri `useExitTime` zatvorenie v `exit`,
  5. **naked POC** (len pri `useNpoc` alebo cieli `npoc`): profil dňa `vpStart`–`vpEnd` (objem baru
     rovnomerne po riadkoch `vpRowTicks`, `VolumeProfile` zo stratégie Volume Profile POC); po konci dňa je
     jeho POC naked, kým ho sviečka nedotkne; drží sa z posledných `npocDays` dní. Filter pustí long len
     s naked POC nad cenou, short len pod ňou.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import (DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, DrawUpdate, LabelStyle,
                                   LineStyle, with_alpha)
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from ..svp.engine import VolumeProfile
from .config import AsiaSweepConfig, EntryModel, SlMode, TpMode
from .drawing import AS_ENTRY, AS_NPOC, AS_RANGE, AS_SWEEP

__all__ = ["AsiaSweepEngine"]

NY = ZoneInfo("America/New_York")
_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_RANGE_COLOR = "#a855f7"
_SWEEP_COLOR = "#f59e0b"
_NPOC_COLOR = "#38bdf8"


@dataclass(slots=True)
class _Npoc:
    price: float
    born: int   #: čas (ms), od ktorého je POC naked (prvý bar po konci dňa profilu)
    seq: int    #: poradové číslo dňa profilu


@dataclass(slots=True)
class _Side:
    """Setup jednej strany rangu: high = vybratie maxima (short), low = vybratie minima (long)."""

    started: bool = False
    extreme: float = 0.0
    bar_idx: int = -1
    reclaimed: bool = False
    dead: bool = False
    done: bool = False


class AsiaSweepEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: AsiaSweepConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=8, atr_len=int(cfg.atrLen))
        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrLen}", self.history.atr_warmup_bars)
        self.required_history = self.warmup.chart_bars
        # cyklus = od začiatku rangu Ázie po ďalší začiatok
        self._prev_rel: int | None = None
        self._cycle_t: int | None = None
        self._valid = False          #: range videný od začiatku (beh nezačal v jeho polovici)
        self.range_hi: float | None = None
        self.range_lo: float | None = None
        self._range_ok = False       #: range uzavretý a prešiel filtrom veľkosti
        self.hi = _Side()
        self.lo = _Side()
        self._trades = 0
        self._entry_cycle: int | None = None
        self._box: tuple[int, bool] | None = None
        # volume profile dňa a naked POC
        self._vp_on = cfg.useNpoc or cfg.tpMode is TpMode.NPOC
        self._vp: VolumeProfile | None = None
        self._vp_valid = False
        self._vp_prev: int | None = None
        self._vp_seq = 0
        self.npocs: list[_Npoc] = []

    # ------------------------------------------------------------------ #

    def _vp_close(self, bar: Bar, out: EngineOutput) -> None:
        """Deň profilu skončil: jeho POC je odteraz naked."""
        if self._vp is not None and self._vp_valid and self._vp.poc is not None:
            self._vp_seq += 1
            n = _Npoc(self._vp.poc, bar.time, self._vp_seq)
            self.npocs.append(n)
            if self.cfg.showNpoc:
                out.drawings.append(DrawLine(AS_NPOC, bar.time, n.price, bar.time + self.step_ms, n.price, _NPOC_COLOR,
                                             style=LineStyle.DASHED, obj_id=f"as.n.{bar.time}", text="nPOC"))
        self._vp = None
        keep = self._vp_seq - int(self.cfg.npocDays)
        self.npocs = [n for n in self.npocs if n.seq > keep]

    def _vp_bar(self, bar: Bar, minute: int, out: EngineOutput) -> None:
        cfg = self.cfg
        length = (cfg.vp_end - cfg.vp_start) % 1440 or 1440
        rel = (minute - cfg.vp_start) % 1440
        inside = rel < length
        prev = self._vp_prev
        self._vp_prev = rel
        if inside and (prev is None or rel < prev or prev >= length):
            self._vp_close(bar, out)
            self._vp = VolumeProfile(cfg.vpRowTicks * self.inst.tick_size)
            self._vp_valid = prev is not None or rel == 0
        elif not inside and prev is not None and prev < length:
            self._vp_close(bar, out)
        # dotyk: naked POC, ktorý sviečka po konci jeho dňa prešla, prestáva byť naked
        end = bar.time + self.step_ms
        alive = []
        for n in self.npocs:
            if bar.low <= n.price <= bar.high:
                continue
            alive.append(n)
            if cfg.showNpoc:
                out.drawings.append(DrawUpdate(f"as.n.{n.born}", "x2_ms", end))
        self.npocs = alive
        if inside and self._vp is not None:
            self._vp.add(bar)

    def _npoc_toward(self, long: bool, price: float) -> float | None:
        """Najbližší naked POC v smere obchodu (long nad cenou, short pod ňou)."""
        cands = [n.price for n in self.npocs if (n.price > price if long else n.price < price)]
        if not cands:
            return None
        return min(cands) if long else max(cands)

    def _rel(self, minute: int) -> int:
        """Minúty od začiatku rangu Ázie (cyklus ide cez polnoc)."""
        return (minute - self.cfg.asia_start) % 1440

    def _imbalance(self, long: bool, atr: float) -> bool:
        if not self.history.has(2):
            return False
        b0, b1, b2 = self.history[0], self.history[1], self.history[2]
        min_size = self.cfg.imbMinSize.resolve(self.inst, price=b0.close, atr=atr)
        if long:
            return b0.low > b2.high and b1.close > b2.high and (b0.low - b2.high) >= min_size
        return b0.high < b2.low and b1.close < b2.low and (b2.low - b0.high) >= min_size

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
        if m is EntryModel.ANY:
            return self._imbalance(long, atr) or self._pinbar(bar, long)
        return bar.close > bar.open if long else bar.close < bar.open

    def _plan(self, long: bool, side: _Side, bar: Bar, atr: float) -> TradePlan | None:
        cfg = self.cfg
        entry = bar.close
        buf = cfg.slBuffer.resolve(self.inst, price=entry, atr=atr)
        if cfg.slMode is SlMode.SWEEP:
            stop = side.extreme - buf if long else side.extreme + buf
        elif cfg.slMode is SlMode.SIGNAL:
            recent = [self.history[i] for i in range(min(3, len(self.history)))]
            stop = min(b.low for b in recent) - buf if long else max(b.high for b in recent) + buf
        else:
            d = cfg.slAtr.resolve(self.inst, price=entry, atr=atr)
            stop = entry - d if long else entry + d
        sl = entry - stop if long else stop - entry
        if sl < 2 * self.inst.tick_size:
            return None
        npoc = self._npoc_toward(long, entry) if cfg.tpMode is TpMode.NPOC else None
        if cfg.tpMode is TpMode.RR or (cfg.tpMode is TpMode.NPOC and npoc is None):
            take = entry + sl * cfg.rrRatio if long else entry - sl * cfg.rrRatio
        elif cfg.tpMode is TpMode.NPOC:
            take = npoc
        elif cfg.tpMode is TpMode.RANGE:
            take = self.range_hi if long else self.range_lo
        else:
            take = (self.range_hi + self.range_lo) / 2.0
        if (long and take <= entry) or (not long and take >= entry):
            return None   # cieľ je už za cenou
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    # ------------------------------------------------------------------ #

    def _new_cycle(self, out: EngineOutput, bar: Bar, valid: bool) -> None:
        self._cycle_t = bar.time
        self._valid = valid
        self.range_hi, self.range_lo = bar.high, bar.low
        self._range_ok = False
        self.hi, self.lo = _Side(), _Side()
        self._trades = 0
        if self.cfg.showRange:
            out.drawings.append(DrawBox(AS_RANGE, bar.time, bar.high, bar.time + self.step_ms, bar.low, _RANGE_COLOR,
                                        fill_color=with_alpha(_RANGE_COLOR, 88), obj_id=f"as.r.{bar.time}",
                                        text="Ázia"))

    def _sweep_label(self, out: EngineOutput, bar: Bar, high: bool) -> None:
        if self.cfg.showSweeps:
            out.drawings.append(DrawLabel(
                AS_SWEEP, bar.time, bar.high if high else bar.low, "sweep", _SWEEP_COLOR,
                style=LabelStyle.NONE, above=high, obj_id=f"as.s{'h' if high else 'l'}.{bar.time}"))

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        atr = self.history.atr
        local = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        rel = self._rel(local.hour * 60 + local.minute)
        close_local = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
        rel_close = self._rel(close_local.hour * 60 + close_local.minute)
        asia_len = self._rel(cfg.asia_end)
        in_asia = rel < asia_len
        new_cycle = in_asia and (self._prev_rel is None or rel < self._prev_rel or self._prev_rel >= asia_len)
        first = self._prev_rel is None
        self._prev_rel = rel
        if self._vp_on:
            self._vp_bar(bar, local.hour * 60 + local.minute, out)

        # ---- boxy obchodu rastú, kým obchod beží ------------------------- #
        end = bar.time + self.step_ms
        if self._box is not None:
            t0, was_open = self._box
            for kind in ("tp", "sl"):
                out.drawings.append(DrawUpdate(f"as.{kind}.{t0}", "x2_ms", end))
            if ctx.position_size != 0.0:
                self._box = (t0, True)
            elif was_open or bar.time > t0:
                self._box = None

        # ---- 1. range Ázie ------------------------------------------------ #
        if new_cycle:
            self._new_cycle(out, bar, valid=not first or rel == 0)
        elif in_asia and self._cycle_t is not None:
            self.range_hi = max(self.range_hi, bar.high)
            self.range_lo = min(self.range_lo, bar.low)
            if cfg.showRange:
                t0 = self._cycle_t
                out.drawings.append(DrawUpdate(f"as.r.{t0}", "y1", self.range_hi))
                out.drawings.append(DrawUpdate(f"as.r.{t0}", "y2", self.range_lo))
        if self._cycle_t is not None and not in_asia and not self._range_ok and self._valid:
            size = (self.range_hi - self.range_lo) / self.range_lo * 100.0 if self.range_lo else 0.0
            ok = size > 0 and (cfg.rangeMinPct.value <= 0 or size >= cfg.rangeMinPct.value) and \
                (cfg.rangeMaxPct.value <= 0 or size <= cfg.rangeMaxPct.value)
            self._range_ok = ok
            if not ok:
                self._valid = False
        if cfg.showRange and self._cycle_t is not None and rel_close <= max(self._rel(cfg.entry_end), asia_len):
            out.drawings.append(DrawUpdate(f"as.r.{self._cycle_t}", "x2_ms", end))

        # ---- výstup v čase ------------------------------------------------- #
        if ctx.position_size != 0.0:
            if cfg.useExitTime and (rel_close >= self._rel(cfg.exit_time) or self._entry_cycle != self._cycle_t):
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                                  reason=f"výstup {cfg.exitH}:{cfg.exitM:02d}"))
            return out
        if not self._range_ok or atr <= 0:
            return out

        # ---- 2. sweep ------------------------------------------------------ #
        in_sweep = self._rel(cfg.sweep_start) <= rel < self._rel(cfg.sweep_end)
        need = max(cfg.sweepMin.resolve(self.inst, price=bar.close, atr=atr), self.inst.tick_size)
        max_d = cfg.maxSweep.resolve(self.inst, price=bar.close, atr=atr)
        for side, high in ((self.hi, True), (self.lo, False)):
            level = self.range_hi if high else self.range_lo
            if side.done or side.dead:
                continue
            if not side.started:
                beyond = bar.high >= level + need if high else bar.low <= level - need
                if in_sweep and beyond:
                    side.started, side.bar_idx = True, idx
                    side.extreme = bar.high if high else bar.low
                    self._sweep_label(out, bar, high)
                else:
                    continue
            side.extreme = max(side.extreme, bar.high) if high else min(side.extreme, bar.low)
            if max_d > 0 and abs(side.extreme - level) > max_d:
                side.dead = True
                continue
            if bar.close < level if high else bar.close > level:
                side.reclaimed = True

        # ---- 3. vstup ------------------------------------------------------ #
        if self._trades >= cfg.maxTradesPerDay or rel >= self._rel(cfg.entry_end):
            return out
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return out
        for side, long in ((self.lo, True), (self.hi, False)):
            if not side.started or side.done or side.dead:
                continue
            if (long and not cfg.allow_long) or (not long and not cfg.allow_short):
                continue
            if idx - side.bar_idx > cfg.entryBars:
                side.dead = True
                continue
            if cfg.requireReclaim and not side.reclaimed:
                continue
            if not self._signal(bar, long, atr):
                continue
            if cfg.useNpoc and self._npoc_toward(long, bar.close) is None:
                continue   # v smere obchodu nie je naked POC — trh tam nemá kam ísť
            plan = self._plan(long, side, bar, atr)
            if plan is None:
                continue
            out.orders.append(OrderIntent(OrderAction.ENTRY, f"as:{idx}", idx, direction=plan.direction, plan=plan,
                                          order_type=OrderType.MARKET,
                                          reason=f"sweep {'minima' if long else 'maxima'} Ázie, model {cfg.entryModel.value}"))
            side.done = True
            self._trades += 1
            self._entry_cycle = self._cycle_t
            for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR),
                                       (DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR)):
                out.drawings.append(DrawBox(kind, bar.time, max(plan.entry, level), end, min(plan.entry, level), color,
                                            fill_color=with_alpha(color, 80), obj_id=f"as.{kind[:2]}.{bar.time}",
                                            text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self._box = (bar.time, False)
            out.drawings.append(DrawLabel(
                AS_ENTRY, bar.time, bar.low if long else bar.high, "LONG" if long else "SHORT", "#ffffff",
                style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"as.e.{bar.time}"))
            break
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
