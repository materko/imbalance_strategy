"""Engine INTRADAY 1.0: daily bias + likvidita PDH/PDL → SD zóna 1H → 15m → 5m → limitka v NY seanse.

Priebeh na každom uzavretom bare grafu (`_update` — to isté aj pre predhistóriu pred behom):

  1. **deň** — denné zavretia RTH (bias), high/low predošlého RTH dňa (PDH/PDL), low/high od otvorenia
     Globexu 18:00 NY (bolo zobratie likvidity?),
  2. **zóny** — bary 60m a 15m sa skladajú z grafu (`StructAggregator`, bar TF sa uzavrie na poslednom bare
     grafu svojej periódy), 5m sú bary grafu. Na každom TF rovnaké pravidlo: báza + impulz + odchod zavretím
     za bázou o `legOutMinAtr` ATR toho TF; zóna vzniká až na bare, ktorý odchod dokončil (bez pohľadu dopredu).
     vnorenie podľa polohy, nie poradia vzniku: 15m zóna platí, keď jej stred leží v živej 1H zóne rovnakého
     smeru, 5m v živej 15m (15m zóna býva súčasťou tej istej bázy, z ktorej 1H zóna vyrástla),
  3. **život zóny** — zavretie za distal ju zlomí, po `zoneAge*` hodinách vyprší; zóna vstupného TF sa dotykom
     minie (prvý návrat),
  4. **vstup** — limitka na proximal najbližšej čerstvej zóny vstupného TF v smere biasu (po zobratí likvidity),
     platí na ďalší bar a kým zóna žije, obnovuje sa; alebo po dotyku sviečka odmietnutia (market).

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

from ..jss.engine import StructAggregator
from .config import ZONE_TFS, BiasMode, EntryModel, IntradayConfig, LiqMode, TpMode
from .drawing import ID_ENTRY, ID_LIQ, ID_SWEEP, ID_ZONE

__all__ = ["IntradayEngine"]

NY = ZoneInfo("America/New_York")
RTH_OPEN, RTH_CLOSE = 570, 960          # 9:30, 16:00 NY (minúty dňa pri zavretí baru)
LONG_COLOR, SHORT_COLOR = "#10b981", "#ef4444"
TF_COLOR = {60: "#3b82f6", 15: "#a855f7", 5: "#f59e0b"}


@dataclass
class _Zone:
    tf: int
    direction: Direction          # LONG = demand, SHORT = supply
    top: float
    bottom: float
    base_ms: int                  # čas prvej sviečky bázy (odtiaľ sa kreslí)
    born_ms: int                  # čas zavretia baru, ktorý odchod dokončil
    expires_ms: int
    uid: int
    fresh: bool = True            # ešte sa jej cena po vzniku nedotkla
    alive: bool = True            # nezlomená a nevypršaná
    used: bool = False            # vstupná zóna: obchod alebo dotyk ju minul

    @property
    def long(self) -> bool:
        return self.direction is Direction.LONG

    @property
    def proximal(self) -> float:
        return self.top if self.long else self.bottom

    @property
    def distal(self) -> float:
        return self.bottom if self.long else self.top

    @property
    def height(self) -> float:
        return self.top - self.bottom

    @property
    def mid(self) -> float:
        return (self.top + self.bottom) / 2.0



@dataclass
class _Candidate:
    zone: _Zone
    start: int                    # index TF baru impulzu
    target: float                 # zavretie, ktoré treba prekonať
    base_high: float
    base_low: float


class _ZoneFinder:
    """SD zóny jedného TF z jeho uzavretých barov — pravidlo bázy, impulzu a odchodu (ako `sdzone`)."""

    def __init__(self, tf: int, cfg: IntradayConfig, inst: InstrumentSpec) -> None:
        self.tf, self.cfg, self.inst = tf, cfg, inst
        self.ms = tf * 60_000
        n = int(cfg.baseMaxBars) + int(cfg.legOutMaxBars) + 4
        self.hist = BarHistory(maxlen=n + int(cfg.atrLen) + 8, atr_len=int(cfg.atrLen))
        self.cands: list[_Candidate] = []
        self.idx = -1
        self._seen: set[tuple[int, Direction]] = set()

    @staticmethod
    def _body_pct(b: Bar) -> float:
        span = b.high - b.low
        return abs(b.close - b.open) / span * 100.0 if span > 0 else 0.0

    def push(self, b: Bar, uid_next) -> list[_Zone]:
        """Uzavretý bar TF → zóny, ktorých odchod sa na ňom dokončil."""
        cfg = self.cfg
        atr_prev = self.hist.atr
        self.hist.append(b)
        self.idx += 1
        atr = self.hist.atr
        born_ms = b.time + self.ms
        new: list[_Zone] = []
        # odchod čakajúcich kandidátov
        keep: list[_Candidate] = []
        for c in self.cands:
            z = c.zone
            if self.idx > c.start and ((b.low <= z.top) if z.long else (b.high >= z.bottom)):
                z.fresh = False
            if (b.close >= c.target) if z.long else (b.close <= c.target):
                z.born_ms = born_ms
                z.expires_ms = born_ms + int(cfg.zone_age_h(self.tf)) * 3_600_000
                new.append(z)
                continue
            if (b.close < c.base_low) if z.long else (b.close > c.base_high):
                continue
            if self.idx - c.start + 1 >= max(1, int(cfg.legOutMaxBars)):
                continue
            keep.append(c)
        self.cands = keep
        # nový kandidát: impulz na tomto bare
        cand = self._detect(b, atr, atr_prev, uid_next)
        if cand is not None:
            self.cands.append(cand)
        return new

    def _detect(self, imp: Bar, atr: float, atr_prev: float, uid_next) -> _Candidate | None:
        cfg = self.cfg
        if atr <= 0:
            return None
        body = abs(imp.close - imp.open)
        if body < cfg.impulseMinBodyAtr.resolve(self.inst, price=imp.close, atr=atr) \
                or self._body_pct(imp) < cfg.impulseMinBodyPct:
            return None
        up = imp.close > imp.open
        for n in range(int(cfg.baseMaxBars), 0, -1):       # najdlhšia báza prvá (celá konsolidácia)
            if not self.hist.has(n + 1):
                continue
            base = [self.hist[i] for i in range(1, n + 1)]
            if any(self._body_pct(x) > cfg.baseMaxBodyPct for x in base):
                continue
            hi, lo = max(x.high for x in base), min(x.low for x in base)
            if hi <= lo:
                continue
            if up:   # demand: proximal na najvyššom tele bázy, distal na najnižšom knôte
                top, bottom = max(max(x.open, x.close) for x in base), lo
            else:    # supply: proximal na najnižšom tele, distal na najvyššom knôte
                top, bottom = hi, min(min(x.open, x.close) for x in base)
            if top <= bottom:
                continue
            d = Direction.LONG if up else Direction.SHORT
            key = (base[-1].time, d)
            if key in self._seen:
                return None
            self._seen.add(key)
            leg = cfg.legOutMinAtr.resolve(self.inst, price=imp.close, atr=atr_prev if atr_prev > 0 else atr)
            z = _Zone(self.tf, d, top, bottom, base[-1].time, 0, 0, uid_next())
            return _Candidate(z, self.idx, hi + leg if up else lo - leg, hi, lo)
        return None


class IntradayEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: IntradayConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        self.history = BarHistory(maxlen=int(cfg.atrLen) + 8, atr_len=int(cfg.atrLen))
        entry_tf = int(cfg.entryTF)
        self.tfs = [t for t in ZONE_TFS if t >= entry_tf]            # 60 → … → vstupný TF
        self.finders = {t: _ZoneFinder(max(t, self.tf), cfg, inst) for t in self.tfs}
        self.aggs = {t: StructAggregator(t, self.tf) for t in self.tfs if t > self.tf}
        self.zones: dict[int, list[_Zone]] = {t: [] for t in self.tfs}
        self._uid = 0
        self.idx = -1
        # deň a likvidita
        self.closes: list[float] = []         # denné zavretia RTH
        self.ema: float | None = None
        self.pdh: float | None = None
        self.pdl: float | None = None
        self._rth_day = None
        self._rth_hi = self._rth_lo = self._rth_close = None
        self._gx_day = None
        self.sess_hi: float | None = None     # od otvorenia Globexu 18:00 NY
        self.sess_lo: float | None = None
        self._liq_drawn: set = set()
        self._zone_drawn: set[int] = set()
        # obchod
        self._pending: tuple[str, int, _Zone, TradePlan] | None = None
        self._trade_day = None
        self._trades_today = 0
        self._boxes: list[str] = []
        self._was_in = False
        # predhistória: zóny 1H, denné zavretia pre EMA a PDH/PDL
        days = max(int(cfg.biasEmaLen * 1.5) + 7, int(cfg.zoneAge60) // 24 + 4, 5)
        self.warmup = Warmup(self.tf).add_seeded("zóny, denné zavretia, PDH/PDL", days * 1440 // self.tf,
                                                 self.tf, self._seed)
        self.required_history = self.warmup.chart_bars

    # ------------------------------------------------------------------ #

    def _next_uid(self) -> int:
        self._uid += 1
        return self._uid

    @property
    def bias(self) -> Direction | None:
        """Smer dňa z dokončených RTH dní; None = bez obchodu, oba smery pri vypnutom biase."""
        cfg = self.cfg
        if cfg.biasMode is BiasMode.OFF:
            return None
        if cfg.biasMode is BiasMode.CLOSE2:
            if len(self.closes) < 2 or self.closes[-1] == self.closes[-2]:
                return None
            return Direction.LONG if self.closes[-1] > self.closes[-2] else Direction.SHORT
        if self.ema is None or len(self.closes) < int(cfg.biasEmaLen) or self.closes[-1] == self.ema:
            return None
        return Direction.LONG if self.closes[-1] > self.ema else Direction.SHORT

    def _liq_ok(self, d: Direction, z: "_Zone | None" = None) -> bool:
        cfg = self.cfg
        if cfg.liqMode is LiqMode.OFF:
            return True
        if cfg.liqMode is LiqMode.ZONE:
            if z is None:
                return False
            atr = self.history.atr
            tol = cfg.liqTolAtr.resolve(self.inst, price=z.proximal, atr=atr) if atr > 0 else 0.0
            if d is Direction.LONG:
                return self.pdl is not None and z.proximal <= self.pdl + tol
            return self.pdh is not None and z.proximal >= self.pdh - tol
        if d is Direction.LONG:
            return self.pdl is not None and self.sess_lo is not None and self.sess_lo < self.pdl
        return self.pdh is not None and self.sess_hi is not None and self.sess_hi > self.pdh

    def _finish_rth(self) -> None:
        if self._rth_day is None or self._rth_close is None:
            return
        self.pdh, self.pdl = self._rth_hi, self._rth_lo
        c = self._rth_close
        self.closes.append(c)
        if len(self.closes) > 400:
            self.closes = self.closes[-400:]
        k = 2.0 / (int(self.cfg.biasEmaLen) + 1)
        self.ema = c if self.ema is None else self.ema + k * (c - self.ema)
        self._rth_day, self._rth_close = None, None

    def _update(self, bar: Bar, out: EngineOutput | None) -> None:
        """Stav dňa, likvidita a zóny po uzavretí baru grafu (bez obchodov) — aj pre predhistóriu."""
        cfg = self.cfg
        self.idx += 1
        self.history.append(bar)
        close_ms = bar.time + self.step_ms
        t = datetime.fromtimestamp(close_ms / 1000, tz=NY)
        m = t.hour * 60 + t.minute
        day = (t.year, t.month, t.day)
        # Globex deň začína 18:00 NY
        g = datetime.fromtimestamp((bar.time + 6 * 3_600_000) / 1000, tz=NY)
        gday = (g.year, g.month, g.day)
        rth = RTH_OPEN < m <= RTH_CLOSE
        if self._rth_day is not None and (not rth or day != self._rth_day):
            self._finish_rth()
        if gday != self._gx_day:
            self._gx_day, self.sess_hi, self.sess_lo = gday, bar.high, bar.low
        else:
            self.sess_hi, self.sess_lo = max(self.sess_hi, bar.high), min(self.sess_lo, bar.low)
        if rth:
            if self._rth_day != day:
                self._rth_day, self._rth_hi, self._rth_lo = day, bar.high, bar.low
            self._rth_hi, self._rth_lo = max(self._rth_hi, bar.high), min(self._rth_lo, bar.low)
            self._rth_close = bar.close
        if out is not None and cfg.showLiquidity and rth and self.pdh is not None and day not in self._liq_drawn:
            self._liq_drawn.add(day)
            end = close_ms + (RTH_CLOSE - m) * 60_000
            for name, y in (("PDH", self.pdh), ("PDL", self.pdl)):
                out.drawings.append(DrawLine(ID_LIQ, bar.time, y, end, y, "#94a3b8", style=LineStyle.DOTTED,
                                             obj_id=f"id.{name}.{day}", text=name))

        # zóny zhora nadol: najprv sa uzavrú bary vyšších TF, až potom vznikajú vnorené zóny nižších
        for tf in self.tfs:
            closed = self.aggs[tf].push(bar) if tf in self.aggs else [bar]
            for b in closed:
                for z in self.finders[tf].push(b, self._next_uid):
                    self._add_zone(z, out)
        # život zón na bare grafu
        for tf in self.tfs:
            live: list[_Zone] = []
            for z in self.zones[tf]:
                if close_ms > z.expires_ms or ((bar.close < z.bottom) if z.long else (bar.close > z.top)):
                    z.alive = False
                    continue
                if (bar.low <= z.proximal) if z.long else (bar.high >= z.proximal):
                    z.fresh = False
                live.append(z)
            self.zones[tf] = live

    def _add_zone(self, z: _Zone, out: EngineOutput | None) -> None:
        self.zones[z.tf].append(z)
        if z.tf == self.tfs[0]:          # zóny najvyššieho TF sa kreslia hneď, nižšie až vo vnorení
            self._draw_zone(z, out)

    def _draw_zone(self, z: _Zone, out: EngineOutput | None) -> None:
        if out is None or not self.cfg.showZones or z.uid in self._zone_drawn:
            return
        self._zone_drawn.add(z.uid)
        col = TF_COLOR.get(z.tf, "#94a3b8")
        out.drawings.append(DrawBox(ID_ZONE, z.base_ms, z.top, z.expires_ms, z.bottom, col,
                                    fill_color=with_alpha(col, 40), obj_id=f"id.z.{z.uid}",
                                    text=f"{'demand' if z.long else 'supply'} {z.tf}m"))

    def _chain(self, z: _Zone) -> list[_Zone] | None:
        """Zóny vyšších TF, v ktorých `z` leží (stred v živej zóne rovnakého smeru o TF vyššie); None = nevnorená."""
        chain, cur = [], z
        for tf in reversed(self.tfs[: self.tfs.index(z.tf)]):
            parents = [p for p in self.zones[tf] if p.alive and p.direction is cur.direction
                       and p.bottom <= cur.mid <= p.top]
            if not parents:
                return None
            cur = max(parents, key=lambda p: p.born_ms)
            chain.append(cur)
        return chain

    def _seed(self, closed: list[Bar], partial: Bar | None) -> None:
        for bar in closed:
            self._update(bar, None)

    # ------------------------------------------------------------------ #

    def _plan(self, z: _Zone, entry: float) -> TradePlan | None:
        cfg = self.cfg
        atr = self.history.atr
        buf = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr) if atr > 0 else 0.0
        stop = z.distal - buf if z.long else z.distal + buf
        sl = abs(entry - stop)
        if sl < self.inst.tick_size * 2 or (z.long and stop >= entry) or (not z.long and stop <= entry):
            return None
        if cfg.tpMode is TpMode.LIQUIDITY:
            target = self.pdh if z.long else self.pdl
            dist = (target - entry) if (target is not None and z.long) else \
                   (entry - target) if target is not None else 0.0
            if dist <= 0 or (cfg.minRR > 0 and dist < cfg.minRR * sl):
                return None
        else:
            dist = cfg.rrRatio * sl
        take = entry + dist if z.long else entry - dist
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        return TradePlan(direction=z.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty if qty > 0 else 1.0, sl_distance=sl)

    def _draw_trade(self, out: EngineOutput, t: int, plan: TradePlan, z: _Zone) -> None:
        long = plan.direction is Direction.LONG
        self._boxes = []
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, LONG_COLOR),
                                   (DrawKind.SL_BOX, plan.stop_loss, SHORT_COLOR)):
            oid = f"id.{'tp' if kind == DrawKind.TP_BOX else 'sl'}.{t}"
            out.drawings.append(DrawBox(kind, t, max(plan.entry, level), t + self.step_ms, min(plan.entry, level),
                                        color, fill_color=with_alpha(color, 80), obj_id=oid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self._boxes.append(oid)
        out.drawings.append(DrawLabel(ID_ENTRY, t, plan.entry, f"{'LONG' if long else 'SHORT'} {z.tf}m zóna",
                                      "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=LONG_COLOR if long else SHORT_COLOR, obj_id=f"id.e.{t}"))

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        cfg, out = self.cfg, EngineOutput()
        pos = ctx.position_size
        # boxy bežiaceho obchodu rastú doprava
        if self._boxes:
            for oid in self._boxes:
                out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
            if pos != 0.0:
                self._was_in = True
            elif self._was_in:
                self._boxes, self._was_in = [], False
        # limitka z minulého baru: vyplnená, alebo zrušiť
        if self._pending is not None:
            oid, pidx, pz, plan = self._pending
            # vyplnená: pozícia beží, alebo sa vyplnila a zavrela v tom istom bare (runner ju hlási v open_order_ids)
            if pos != 0.0 or oid in ctx.open_order_ids:
                pz.used = True
                self._trades_today += 1
                self._draw_trade(out, bar.time, plan, pz)
                self._was_in = pos != 0.0
                if not self._was_in:          # vyplnená a zavretá v tom istom bare — box ostane na jednom bare
                    self._boxes = []
            else:
                out.orders.append(OrderIntent(OrderAction.CANCEL, oid, pidx, reason="nevyplnené"))
            self._pending = None

        fresh_before = {z.uid for tf in self.tfs for z in self.zones[tf] if z.fresh}
        self._update(bar, out)
        idx = self.idx
        t = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
        m, day = t.hour * 60 + t.minute, (t.year, t.month, t.day)
        if day != self._trade_day:
            self._trade_day, self._trades_today = day, 0

        if cfg.useExitTime and pos != 0.0 and RTH_OPEN < m and m >= cfg.exit_minutes:
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason="výstup v čase"))
            return out

        start, end = cfg.window
        if pos != 0.0 or not (start < m <= end) or self._trades_today >= int(cfg.maxTradesPerDay):
            return out
        if cfg.weekdaysOnly and t.weekday() >= 5:
            return out
        bias = self.bias
        if cfg.biasMode is not BiasMode.OFF and bias is None:
            return out
        entry_tf = self.tfs[-1]
        cands = []
        chains: dict[int, list[_Zone]] = {}
        for z in self.zones[entry_tf]:
            if not z.alive or z.used:
                continue
            chain = self._chain(z)
            if chain is None:
                continue
            chains[z.uid] = chain
            if bias is not None and z.direction is not bias:
                continue
            if (z.long and not cfg.allow_long) or (not z.long and not cfg.allow_short):
                continue
            if not self._liq_ok(z.direction, z):
                continue
            cands.append(z)
        if not cands:
            return out

        if cfg.entryModel is EntryModel.REJECT:
            # dotyk na tomto bare a zavretie späť mimo zóny v smere obchodu → market na zavretí
            for z in cands:
                if z.uid not in fresh_before or z.fresh:
                    continue
                if (z.long and bar.close > z.top) or (not z.long and bar.close < z.bottom):
                    plan = self._plan(z, bar.close)
                    z.used = True
                    if plan is None:
                        continue
                    oid = f"id:{idx}"
                    out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=z.direction, plan=plan,
                                                  order_type=OrderType.MARKET, reason=f"odmietnutie {z.tf}m zóny"))
                    self._pending = (oid, idx, z, plan)
                    for q in [z, *chains[z.uid]]:
                        self._draw_zone(q, out)
                    return out
            return out

        # dotyk: limitka na proximal (− hĺbka) najbližšej čerstvej zóny, cena musí byť ešte pred ňou
        live = [z for z in cands if z.fresh]
        if not live:
            return out
        def price(z: _Zone) -> float:
            h = z.height * cfg.entryDepthPct / 100.0
            return z.proximal - h if z.long else z.proximal + h
        live = [z for z in live if (bar.close > price(z)) if z.long] + \
               [z for z in live if (bar.close < price(z)) if not z.long]
        if not live:
            return out
        z = min(live, key=lambda q: abs(bar.close - price(q)))
        plan = self._plan(z, price(z))
        if plan is None:
            return out
        oid = f"idL:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=z.direction, plan=plan,
                                      order_type=OrderType.LIMIT, reason=f"{z.tf}m zóna {z.uid}"))
        self._pending = (oid, idx, z, plan)
        for q in [z, *chains[z.uid]]:
            self._draw_zone(q, out)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
