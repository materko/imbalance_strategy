"""Engine SWEEP FVG 1.0: výber likvidity → CHoCH / BOS → limitka na okraji najbližšieho FVG.

Priebeh na každom uzavretom bare grafu (`_update` — to isté aj pre predhistóriu pred behom):

  1. **likvidita** — TF likvidity sa skladajú z grafu (`StructAggregator`, bar TF sa uzavrie na poslednom bare grafu
     svojej periódy); výrazné swingy (`liquidity.levels.SwingFinder`) dajú úrovne, rovnaké sa zlúčia,
  2. **výber** — cena prerazí buy-side úroveň → čaká sa na short (sell-side → long); extrém výberu sa posúva,
     kým cena ide ďalej,
  3. **zlom** — swingy grafu (`structPivotLen`); zavretie (knôt) za posledným swingom pred extrémom výberu je
     CHoCH (proti doterajšiemu smeru štruktúry) alebo BOS (v jeho smere),
  4. **FVG** — medzera medzi 1. a 3. sviečkou v smere obchodu, aspoň `fvgMinAtr` ATR, vzniknutá od extrému
     výberu po zlom (+ `fvgWaitBars`), ešte nedotknutá na úrovni vstupu; vyberie sa podľa `fvgPick`,
  5. **vstup** — limitka na okraji FVG (alebo strede), platí na ďalší bar a obnovuje sa najviac `entryMaxBars`
     barov po zlome; setup zruší cena za stopom alebo v cieli pred vyplnením.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import (DrawBox, DrawCommand, DrawDelete, DrawKind, DrawLabel, DrawLine, DrawUpdate,
                                   LabelStyle, LineStyle, with_alpha)
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from ..jss.engine import StructAggregator
from ..liquidity.levels import Level, SwingFinder
from .config import BreakBy, BreakType, EntryModel, FvgPick, SweepFvgConfig, TpMode
from .drawing import SF_ENTRY, SF_FVG, SF_LIQ_BUY, SF_LIQ_SELL, SF_STRUCT, SF_SWEEP

__all__ = ["SweepFvgEngine"]

NY = ZoneInfo("America/New_York")
LONG_COLOR, SHORT_COLOR = "#10b981", "#ef4444"
BSL_COLOR, SSL_COLOR = "#ef4444d9", "#10b981d9"
FVG_COLOR = "#a855f7"


@dataclass
class _Fvg:
    long: bool            #: býčí FVG (pre long) / medvedí (pre short)
    top: float
    bottom: float
    t0: int               #: čas prvej sviečky
    idx: int              #: index baru, na ktorom vznikol (3. sviečka)
    hi_since: float = float("-inf")   #: extrém ceny po vzniku — či sa cena vrátila k vstupu
    lo_since: float = float("inf")

    @property
    def size(self) -> float:
        return self.top - self.bottom


@dataclass
class _Sweep:
    direction: Direction  #: smer obchodu (po výbere buy-side short)
    level: float
    extreme: float
    extreme_ms: int
    start: int


@dataclass
class _Setup:
    direction: Direction
    extreme: float
    break_idx: int
    sweep_ms: int
    kind: str             #: "CHoCH" / "BOS"
    fvg: _Fvg | None = None
    box_id: str = ""

    @property
    def long(self) -> bool:
        return self.direction is Direction.LONG


class SweepFvgEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: SweepFvgConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        self.history = BarHistory(maxlen=int(cfg.atrLen) + 8, atr_len=int(cfg.atrLen))
        max_age_ms = int(cfg.liqMaxAgeHours) * 3_600_000
        self.finders: list[tuple[StructAggregator, SwingFinder]] = []
        for tf in cfg.active_liq_timeframes():
            if tf < self.tf or tf % self.tf:
                continue   # TF menší ako graf alebo nie jeho násobok sa zo sviečok grafu poskladať nedá
            self.finders.append((StructAggregator(tf, self.tf),
                                 SwingFinder(tf, cfg.liqPivotLen, cfg.liqMinDispAtr.value, cfg.atrLen, max_age_ms)))
        if not self.finders:
            raise ValueError(f"žiadny zapnutý TF likvidity nie je násobkom TF grafu {self.tf}m")
        self.levels: list[Level] = []
        self._gone: set[tuple[str, int, float]] = set()
        self._uid = 0
        self.idx = -1
        # štruktúra grafu
        n = int(cfg.structPivotLen)
        self._win: deque[Bar] = deque(maxlen=2 * n + 1)
        self.swing_hi: deque[tuple[int, float]] = deque(maxlen=200)
        self.swing_lo: deque[tuple[int, float]] = deque(maxlen=200)
        self.trend: Direction | None = None
        self._hi_broken = self._lo_broken = True
        self.fvgs: deque[_Fvg] = deque(maxlen=300)
        self.sweeps: dict[Direction, _Sweep] = {}
        self.setup: _Setup | None = None
        # obchod
        self._pending: tuple[str, int, TradePlan, _Setup] | None = None
        self._trade_day = None
        self._trades_today = 0
        self._boxes: list[str] = []
        self._was_in = False
        # predhistória: likvidita najvyššieho TF + swingy grafu
        top_tf = max(f.tf for _, f in self.finders)
        hours = int(cfg.liqMaxAgeHours) + top_tf * (2 * int(cfg.liqPivotLen) + int(cfg.atrLen) + 2) // 60 + 1
        self.warmup = Warmup(self.tf).add_seeded("likvidita, swingy a FVG", hours * 60 // self.tf + 4 * n,
                                                 self.tf, self._seed)
        self.required_history = self.warmup.chart_bars

    # ------------------------------------------------------------------ #
    # stav (aj predhistória)
    # ------------------------------------------------------------------ #

    def _seed(self, closed: list[Bar], partial: Bar | None) -> None:
        for bar in closed:
            self._update(bar, None)

    def _add_level(self, lv: Level, atr_tf: float) -> None:
        if (lv.side, lv.start_ms, lv.price) in self._gone:
            return
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
        return DrawLine(SF_LIQ_BUY if buy else SF_LIQ_SELL, lv.start_ms, lv.price, end_ms, lv.price,
                        BSL_COLOR if buy else SSL_COLOR, obj_id=f"sf.liq.{lv.side}.{lv.start_ms}.{lv.uid}",
                        text=lv.label)

    def _update(self, bar: Bar, out: EngineOutput | None) -> None:
        cfg = self.cfg
        self.idx += 1
        idx = self.idx
        self.history.append(bar)
        atr = self.history.atr
        draw = out is not None

        # ---- likvidita: nové úrovne z uzavretých barov TF ------------------- #
        for agg, finder in self.finders:
            for closed in agg.push(bar):
                for lv in finder.push(closed):
                    self._add_level(lv, finder.atr)

        # ---- výber likvidity ---------------------------------------------- #
        keep: list[Level] = []
        for lv in self.levels:
            buy = lv.side == "buy"
            if (buy and bar.high > lv.price) or (not buy and bar.low < lv.price):
                self._gone.add((lv.side, lv.start_ms, lv.price))
                if draw and cfg.showLevels:
                    out.drawings.append(self._draw_level(lv, bar.time))
                if lv.strength < int(cfg.liqMinStrength):
                    continue
                if cfg.sweepReclaim and ((buy and bar.close >= lv.price) or (not buy and bar.close <= lv.price)):
                    continue
                d = Direction.SHORT if buy else Direction.LONG
                if (d is Direction.LONG and not cfg.allow_long) or (d is Direction.SHORT and not cfg.allow_short):
                    continue
                ext = bar.high if buy else bar.low
                old = self.sweeps.get(d)
                if old is not None and ((buy and old.extreme >= ext) or (not buy and old.extreme <= ext)):
                    ext, ext_ms = old.extreme, old.extreme_ms
                else:
                    ext_ms = bar.time
                self.sweeps[d] = _Sweep(d, lv.price, ext, ext_ms, idx)
                if draw and cfg.showStructure:
                    out.drawings.append(DrawLabel(SF_SWEEP, bar.time, ext, "výber LQ", "#ffffff",
                                                  style=LabelStyle.DOWN if buy else LabelStyle.UP, above=buy,
                                                  bg_color=SHORT_COLOR if buy else LONG_COLOR,
                                                  obj_id=f"sf.sw.{bar.time}.{lv.side}"))
            elif bar.time >= lv.expires_ms:
                self._gone.add((lv.side, lv.start_ms, lv.price))
                if draw and cfg.showLevels:
                    out.drawings.append(self._draw_level(lv, lv.expires_ms))
            else:
                keep.append(lv)
        self.levels = keep

        # ---- swingy grafu ---------------------------------------------------- #
        n = int(cfg.structPivotLen)
        self._win.append(bar)
        if len(self._win) == 2 * n + 1:
            c = self._win[n]
            left, right = list(self._win)[:n], list(self._win)[n + 1:]
            if all(c.high > x.high for x in left) and all(c.high >= x.high for x in right):
                self.swing_hi.append((c.time, c.high))
                self._hi_broken = False
            if all(c.low < x.low for x in left) and all(c.low <= x.low for x in right):
                self.swing_lo.append((c.time, c.low))
                self._lo_broken = False

        # ---- FVG ----------------------------------------------------------- #
        for f in self.fvgs:
            if f.idx < idx:
                f.hi_since = max(f.hi_since, bar.high)
                f.lo_since = min(f.lo_since, bar.low)
        if self.history.has(3) and atr > 0:
            b0, b2 = self.history[0], self.history[2]
            min_gap = cfg.fvgMinAtr.resolve(self.inst, price=bar.close, atr=atr)
            if b0.low > b2.high and b0.low - b2.high >= min_gap:
                self.fvgs.append(_Fvg(True, b0.low, b2.high, b2.time, idx))
            if b0.high < b2.low and b2.low - b0.high >= min_gap:
                self.fvgs.append(_Fvg(False, b2.low, b0.high, b2.time, idx))

        # ---- zlom štruktúry po výbere --------------------------------------- #
        trend_before = self.trend
        for d in list(self.sweeps):
            s = self.sweeps[d]
            long = d is Direction.LONG
            if s.start < idx:   # extrém výberu sa posúva, kým cena ide ďalej
                if long and bar.low < s.extreme:
                    s.extreme, s.extreme_ms = bar.low, bar.time
                elif not long and bar.high > s.extreme:
                    s.extreme, s.extreme_ms = bar.high, bar.time
            swings = self.swing_hi if long else self.swing_lo
            prior = [sw for sw in swings if sw[0] < s.extreme_ms]
            if prior:
                sw_ms, lvl = prior[-1]
                probe = (bar.high if cfg.breakBy is BreakBy.WICK else bar.close) if long else \
                        (bar.low if cfg.breakBy is BreakBy.WICK else bar.close)
                if (long and probe > lvl) or (not long and probe < lvl):
                    del self.sweeps[d]
                    kind = "BOS" if trend_before is d else "CHoCH"
                    if (cfg.breakType is BreakType.CHOCH and kind != "CHoCH") or \
                            (cfg.breakType is BreakType.BOS and kind != "BOS"):
                        continue
                    self._new_setup(_Setup(d, s.extreme, idx, s.extreme_ms, kind), out)
                    if draw and cfg.showStructure:
                        out.drawings.append(DrawLine(SF_STRUCT, sw_ms, lvl, bar.time, lvl,
                                                     LONG_COLOR if long else SHORT_COLOR, style=LineStyle.DASHED,
                                                     obj_id=f"sf.br.{bar.time}.{d.value}", text=kind))
                    continue
            if idx - s.start >= int(cfg.breakMaxBars):
                del self.sweeps[d]

        # ---- smer štruktúry (pre CHoCH / BOS) ------------------------------- #
        if self.swing_hi and not self._hi_broken and bar.close > self.swing_hi[-1][1]:
            self.trend, self._hi_broken = Direction.LONG, True
        if self.swing_lo and not self._lo_broken and bar.close < self.swing_lo[-1][1]:
            self.trend, self._lo_broken = Direction.SHORT, True

        # ---- setup: výber FVG, zneplatnenie -------------------------------- #
        st = self.setup
        if st is None:
            return
        if idx - st.break_idx > int(cfg.entryMaxBars):
            self._end_setup(out)
            return
        if (st.long and bar.low <= st.extreme) or (not st.long and bar.high >= st.extreme):
            self._end_setup(out)                     # cena za extrémom výberu pred vyplnením
            return
        if idx <= st.break_idx + int(cfg.fvgWaitBars):
            self._pick_fvg(st, bar, out)
        if st.fvg is None:
            if idx >= st.break_idx + int(cfg.fvgWaitBars):
                self._end_setup(out)
            return
        plan = self._plan(st, self._entry_price(st.fvg))
        if plan is None:
            self._end_setup(out)
            return
        if (st.long and bar.high >= plan.take_profit) or (not st.long and bar.low <= plan.take_profit):
            self._end_setup(out)                     # cieľ dosiahnutý bez nás
            return
        if (st.long and st.fvg.lo_since <= self._entry_price(st.fvg)) or \
                (not st.long and st.fvg.hi_since >= self._entry_price(st.fvg)):
            self._end_setup(out)                     # FVG dotknutý bez vyplnenia (limitka nebola živá)

    # ------------------------------------------------------------------ #
    # setup
    # ------------------------------------------------------------------ #

    def _new_setup(self, st: _Setup, out: EngineOutput | None) -> None:
        if self.setup is not None:
            self._end_setup(out)
        self.setup = st

    def _end_setup(self, out: EngineOutput | None) -> None:
        self.setup = None

    def _entry_price(self, f: _Fvg) -> float:
        if self.cfg.entryLevel is EntryModel.MID:
            return (f.top + f.bottom) / 2.0
        return f.top if f.long else f.bottom          # okraj, ku ktorému sa cena vracia

    def _pick_fvg(self, st: _Setup, bar: Bar, out: EngineOutput | None) -> None:
        cfg = self.cfg
        cands = []
        for f in self.fvgs:
            if f.long is not st.long or f.t0 < st.sweep_ms or f.idx > st.break_idx + int(cfg.fvgWaitBars):
                continue
            e = self._entry_price(f)
            if (st.long and f.lo_since <= e) or (not st.long and f.hi_since >= e):
                continue                              # cena sa k vstupu už vrátila
            if (st.long and e <= st.extreme) or (not st.long and e >= st.extreme):
                continue
            cands.append(f)
        if not cands:
            return
        if cfg.fvgPick is FvgPick.LARGEST:
            best = max(cands, key=lambda f: f.size)
        elif cfg.fvgPick is FvgPick.FIRST:
            best = min(cands, key=lambda f: f.idx)
        else:
            best = min(cands, key=lambda f: abs(bar.close - self._entry_price(f)))
        if best is st.fvg:
            return
        if out is not None and st.box_id:
            out.drawings.append(DrawDelete(st.box_id))
        st.fvg = best
        st.box_id = ""
        if out is not None and cfg.showFvg:
            st.box_id = f"sf.fvg.{best.t0}.{best.idx}"
            out.drawings.append(DrawBox(SF_FVG, best.t0, best.top, bar.time + self.step_ms, best.bottom, FVG_COLOR,
                                        fill_color=with_alpha(FVG_COLOR, 50), obj_id=st.box_id,
                                        text=f"FVG {st.kind}"))

    def _plan(self, st: _Setup, entry: float) -> TradePlan | None:
        cfg = self.cfg
        atr = self.history.atr
        buf = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr) if atr > 0 else 0.0
        stop = st.extreme - buf if st.long else st.extreme + buf
        sl = abs(entry - stop)
        if sl < self.inst.tick_size * 2 or (st.long and stop >= entry) or (not st.long and stop <= entry):
            return None
        max_sl = cfg.maxSlAtr.resolve(self.inst, price=entry, atr=atr) if atr > 0 else 0.0
        if max_sl > 0 and sl > max_sl:
            return None
        if cfg.tpMode is TpMode.POINTS:
            dist = cfg.tpPoints.resolve(self.inst, price=entry, atr=atr)
        elif cfg.tpMode is TpMode.LIQUIDITY:
            side = "buy" if st.long else "sell"
            beyond = cfg.minRR * sl
            levels = [lv.price for lv in self.levels if lv.side == side and lv.strength >= int(cfg.liqMinStrength)
                      and ((lv.price > entry + beyond) if st.long else (lv.price < entry - beyond))]
            if not levels:
                return None
            dist = (min(levels) - entry) if st.long else (entry - max(levels))
        else:
            dist = cfg.rrRatio * sl
        if dist <= 0:
            return None
        take = entry + dist if st.long else entry - dist
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        return TradePlan(direction=st.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty if qty > 0 else 1.0, sl_distance=sl)

    # ------------------------------------------------------------------ #
    # bar grafu
    # ------------------------------------------------------------------ #

    def _draw_trade(self, out: EngineOutput, t: int, plan: TradePlan, st: _Setup) -> None:
        long = plan.direction is Direction.LONG
        self._boxes = []
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, LONG_COLOR),
                                   (DrawKind.SL_BOX, plan.stop_loss, SHORT_COLOR)):
            oid = f"sf.{'tp' if kind == DrawKind.TP_BOX else 'sl'}.{t}"
            out.drawings.append(DrawBox(kind, t, max(plan.entry, level), t + self.step_ms, min(plan.entry, level),
                                        color, fill_color=with_alpha(color, 80), obj_id=oid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self._boxes.append(oid)
        out.drawings.append(DrawLabel(SF_ENTRY, t, plan.entry, f"{'LONG' if long else 'SHORT'} {st.kind} FVG",
                                      "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=LONG_COLOR if long else SHORT_COLOR, obj_id=f"sf.e.{t}"))

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
            oid, pidx, plan, pst = self._pending
            # vyplnená: pozícia beží, alebo sa vyplnila a zavrela v tom istom bare (runner ju hlási v open_order_ids)
            if pos != 0.0 or oid in ctx.open_order_ids:
                self._trades_today += 1
                self._draw_trade(out, bar.time, plan, pst)
                self._was_in = pos != 0.0
                if not self._was_in:          # vyplnená a zavretá v tom istom bare — box ostane na jednom bare
                    self._boxes = []
                if self.setup is pst:
                    self.setup = None
            else:
                out.orders.append(OrderIntent(OrderAction.CANCEL, oid, pidx, reason="nevyplnené"))
            self._pending = None

        self._update(bar, out)
        idx = self.idx
        st = self.setup
        if st is not None and st.box_id:
            out.drawings.append(DrawUpdate(st.box_id, "x2_ms", bar.time + self.step_ms))

        t = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
        m, day = t.hour * 60 + t.minute, (t.year, t.month, t.day)
        if day != self._trade_day:
            self._trade_day, self._trades_today = day, 0
        if cfg.useExitTime and pos != 0.0 and m >= cfg.exit_minutes and m - cfg.exit_minutes < self.tf:
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason="výstup v čase"))
            return out

        if pos != 0.0 or st is None or st.fvg is None or self._trades_today >= int(cfg.maxTradesPerDay):
            return out
        if cfg.weekdaysOnly and t.weekday() >= 5:
            return out
        if cfg.useTradeWindow:
            start, end = cfg.window
            if not (start < m <= end):
                return out
        entry = self._entry_price(st.fvg)
        if (st.long and bar.close <= entry) or (not st.long and bar.close >= entry):
            return out
        plan = self._plan(st, entry)
        if plan is None:
            return out
        oid = f"sf:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=st.direction, plan=plan,
                                      order_type=OrderType.LIMIT, reason=f"výber LQ + {st.kind} + FVG"))
        self._pending = (oid, idx, plan, st)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        """Nevybratá likvidita na konci dát — po posledný bar."""
        if not self.cfg.showLevels:
            return []
        end = bar.time + self.step_ms
        return [self._draw_level(lv, end) for lv in self.levels]
