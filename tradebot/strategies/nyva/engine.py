"""Engine NY VA BREAKOUT 1.0 — fixed range volume profile prvej hodiny NY a prieraz z value area.

Priebeh na každom uzavretom bare grafu (čas New York podľa OTVORENIA baru, ako Pine `time`):

  1. **range** — bary otvorené v `rangeStartH:M` ≤ t < `rangeEndH:M` sa zbierajú (high, low, objem),
  2. **profil** — na prvom bare po rangei sa objem každého baru rozloží rovnomerne do `profileRows` riadkov medzi
     jeho low a high; POC = stred riadku s najväčším objemom, value area sa rozširuje od POC vždy o objemnejší
     susedný riadok, kým nemá `valueAreaPct` % objemu (VAH = horná hrana, VAL = dolná),
  3. **prieraz** — `confirmCloses` zavretí po sebe nad VAH (pod VAL); deň so šírkou VA mimo `vaMinPoints`–`vaMaxPoints`
     sa neobchoduje, pri `useVwap` long len nad VWAP dňa (od 18:00 NY), short len pod,
  4. **vstup** — do `entryEndH:M`, bez pozície, najviac `maxTradesPerDay` za deň: ``close`` = market na ďalšej sviečke,
     ``retest`` = limitka na VAH / VAL platná `retestBars` barov,
  5. **stop** `slBufferTicks` tickov za POC (najviac `maxSlPoints` / `maxSlAtr` × ATR: vynechať alebo skrátiť),
     **cieľ** `rrRatio` × riziko; pri `useCloseTime` zavretie v čase. EMA filter je obal vstupu (`trendFilter`).

Engine je čistý: žiadne I/O, žiadny globálny stav. Rovnaké pravidlá ako Pine skript NY VA BREAKOUT 1.0.
"""

from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, DrawUpdate, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import EntryMode, NyVaConfig, SlCap
from .drawing import NV_ENTRY, NV_POC, NV_RANGE, NV_VA

__all__ = ["NyVaEngine", "value_area", "profile_shape"]

NY = ZoneInfo("America/New_York")
_LONG = "#10b981"
_SHORT = "#ef4444"
_RANGE = "#94a3b8"
_POC = "#facc15"
_VA = "#22d3ee"


def value_area(bars: list[tuple[float, float, float]], rows: int, pct: float,
               min_step: float) -> tuple[float, float, float, float, float]:
    """(POC, VAH, VAL, high, low) z barov (high, low, objem) — rovnaký výpočet ako Pine skript."""
    hi = max(b[0] for b in bars)
    lo = min(b[1] for b in bars)
    step = max((hi - lo) / rows, min_step)
    vols = [0.0] * rows
    for h, l, v in bars:
        i0 = max(0, min(rows - 1, math.floor((l - lo) / step)))
        i1 = max(0, min(rows - 1, math.floor((h - lo) / step)))
        share = v / (i1 - i0 + 1)
        for j in range(i0, i1 + 1):
            vols[j] += share
    p = vols.index(max(vols))
    target = sum(vols) * pct / 100.0
    acc, up, dn = vols[p], p, p
    while acc < target and (up < rows - 1 or dn > 0):
        v_up = vols[up + 1] if up < rows - 1 else -1.0
        v_dn = vols[dn - 1] if dn > 0 else -1.0
        if v_up >= v_dn:
            up += 1
            acc += v_up
        else:
            dn -= 1
            acc += v_dn
    return lo + (p + 0.5) * step, lo + (up + 1) * step, lo + dn * step, hi, lo


def profile_shape(bars: list[tuple[float, float, float]], rows: int, pct: float, min_step: float) -> dict[str, float]:
    """Tvar profilu rangeu: poloha POC a stredu value area (0 = low, 1 = high) a podiel objemu v dolnej / hornej tretine.

    P-profil (prieraz hore) = POC a VA hore, tenký chvost dole; b-profil (prieraz dole) zrkadlovo."""
    poc, vah, val, hi, lo = value_area(bars, rows, pct, min_step)
    span = hi - lo
    if span <= 0:
        return {"poc": 0.5, "va": 0.5, "low": 1 / 3, "high": 1 / 3}
    third = span / 3.0
    total = low = high = 0.0
    for h, l, v in bars:
        rng = max(h - l, 1e-12)
        total += v
        low += v * max(0.0, min(h, lo + third) - l) / rng if h > l else (v if l <= lo + third else 0.0)
        high += v * max(0.0, h - max(l, hi - third)) / rng if h > l else (v if h >= hi - third else 0.0)
    total = total or 1.0
    return {"poc": (poc - lo) / span, "va": ((vah + val) / 2 - lo) / span, "low": low / total, "high": high / total}


class NyVaEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: NyVaConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=4, atr_len=14)
        self.warmup = Warmup(self.chart_tf_minutes).add("ATR 14 (max stop)", self.history.atr_warmup_bars)
        self.required_history = max(1, self.warmup.chart_bars)
        self.day = None
        self.bars: list[tuple[float, float, float]] = []
        self.range_ms: int | None = None
        self.prev_in = False
        self.built = False
        self.poc: float | None = None
        self.vah: float | None = None
        self.val: float | None = None
        self.trades = 0
        self.prev_close: float | None = None
        self.prev_min: int | None = None
        self.boxes: list[str] = []
        self.was_in = False
        self.shape: dict[str, float] = {}
        self.shape_p = self.shape_b = False
        self.n_up = 0                 #: zavretí po sebe nad VAH
        self.n_dn = 0                 #: zavretí po sebe pod VAL
        self.pending: tuple[str, int] | None = None   #: nevyplnená limitka retestu (id, index baru)
        self.vwap_day = None
        self.pv = self.vv = 0.0

    # ------------------------------------------------------------------ #

    def _build(self, out: EngineOutput, bar: Bar) -> None:
        cfg = self.cfg
        self.poc, self.vah, self.val, hi, lo = value_area(self.bars, int(cfg.profileRows), float(cfg.valueAreaPct),
                                                          self.inst.tick_size)
        self.built = True
        self.shape = profile_shape(self.bars, int(cfg.profileRows), float(cfg.valueAreaPct), self.inst.tick_size)
        sh = self.shape
        self.shape_p = (sh["poc"] >= cfg.shapePocPct / 100 and sh["va"] >= cfg.shapeVaPct / 100
                        and sh["low"] <= cfg.shapeTailPct / 100)
        self.shape_b = (sh["poc"] <= 1 - cfg.shapePocPct / 100 and sh["va"] <= 1 - cfg.shapeVaPct / 100
                        and sh["high"] <= cfg.shapeTailPct / 100)
        if not cfg.showLevels:
            return
        t = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        x_end = int(datetime(t.year, t.month, t.day, cfg.entryEndH, cfg.entryEndM, tzinfo=NY).timestamp() * 1000)
        x0 = self.range_ms if self.range_ms is not None else bar.time
        x_end = max(x_end, bar.time)
        kind = "P" if self.shape_p else "b" if self.shape_b else "D"
        out.drawings.append(DrawBox(NV_RANGE, x0, hi, bar.time, lo, _RANGE, fill_color=with_alpha(_RANGE, 40),
                                    obj_id=f"nv.r.{x0}", text=f"range · profil {kind}"))
        for kind, y, color, name, width in ((NV_POC, self.poc, _POC, "POC", 2), (NV_VA, self.vah, _VA, "VAH", 1),
                                            (NV_VA, self.val, _VA, "VAL", 1)):
            out.drawings.append(DrawLine(kind, x0, y, x_end, y, color, width=width, obj_id=f"nv.{name}.{x0}",
                                         text=f"{name} {self.inst.round_price(y):g}"))

    def _max_sl(self) -> float:
        cfg, lims = self.cfg, []
        if cfg.maxSlPoints > 0:
            lims.append(float(cfg.maxSlPoints))
        if cfg.maxSlAtr > 0 and self.history.atr > 0:
            lims.append(cfg.maxSlAtr * self.history.atr)
        return min(lims) if lims else 0.0

    def _plan(self, long: bool, entry: float, stop: float) -> TradePlan | None:
        cfg = self.cfg
        risk = abs(entry - stop)
        cap = self._max_sl()
        if cap > 0 and risk > cap:
            if cfg.slCapMode is SlCap.SKIP:
                return None
            risk = cap
            stop = entry - cap if long else entry + cap
        if risk < self.inst.tick_size * 2:
            return None
        take = entry + cfg.rrRatio * risk if long else entry - cfg.rrRatio * risk
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, risk)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=risk)

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, plan: TradePlan, reason: str, text: str,
               limit: bool = False) -> None:
        long = plan.direction is Direction.LONG
        oid = f"nv:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.LIMIT if limit else OrderType.MARKET, reason=reason))
        if limit:
            self.pending = (oid, idx)     # obchod sa započíta až pri vyplnení
        else:
            self.trades += 1
        self.boxes, self.was_in = [], False
        end = bar.time + self.step_ms
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG), (DrawKind.SL_BOX, plan.stop_loss, _SHORT)):
            oid = f"nv.{kind[:2]}.{bar.time}"
            out.drawings.append(DrawBox(kind, bar.time, max(plan.entry, level), end, min(plan.entry, level), color,
                                        fill_color=with_alpha(color, 60), obj_id=oid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(oid)
        out.drawings.append(DrawLabel(NV_ENTRY, bar.time, plan.entry, text, "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"nv.e.{bar.time}"))

    def _track(self, out: EngineOutput, bar: Bar, ctx: MarketContext) -> None:
        """Boxy bežiaceho obchodu rastú doprava; po skončení obchodu prestanú."""
        if not self.boxes:
            return
        for oid in self.boxes:
            out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
        if ctx.position_size != 0.0:
            self.was_in = True
        elif self.was_in:
            self.boxes, self.was_in = [], False

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        self._track(out, bar, ctx)
        t = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        cur = t.hour * 60 + t.minute
        vday = datetime.fromtimestamp(bar.time / 1000 + 6 * 3600, tz=NY).date()   # obchodný deň od 18:00 NY
        if vday != self.vwap_day:
            self.vwap_day, self.pv, self.vv = vday, 0.0, 0.0
        self.pv += (bar.high + bar.low + bar.close) / 3.0 * bar.volume
        self.vv += bar.volume
        vwap = self.pv / self.vv if self.vv > 0 else None
        if t.date() != self.day:
            self.day = t.date()
            self.n_up = self.n_dn = 0
            self.trades, self.built = 0, False
            self.poc = self.vah = self.val = None
            self.bars, self.prev_in, self.prev_min = [], False, None

        # ---- range a profil ------------------------------------------------ #
        in_range = cfg.range_start <= cur < cfg.range_end
        if in_range:
            if not self.prev_in:
                self.bars, self.range_ms, self.built = [], bar.time, False
            self.bars.append((bar.high, bar.low, bar.volume))
        elif self.prev_in and self.bars and not self.built:
            self._build(out, bar)
        self.prev_in = in_range

        # ---- zavretie v čase ----------------------------------------------- #
        pos = ctx.position_size
        if (cfg.useCloseTime and pos != 0.0 and cur >= cfg.close_time
                and (self.prev_min is None or self.prev_min < cfg.close_time)):
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason="zavretie v čase"))

        # ---- retest: vyplnenie / zrušenie limitky -------------------------- #
        if self.pending is not None:
            oid, at = self.pending
            if pos != 0.0:
                self.pending = None
                self.trades += 1
            elif idx - at >= int(cfg.retestBars) or cur >= cfg.entry_end or out.close_session:
                out.orders.append(OrderIntent(OrderAction.CANCEL, oid, at, reason="retest nevyplnený"))
                self.pending = None

        # ---- prieraz a vstup ------------------------------------------------ #
        if self.built and not in_range:
            c = bar.close
            self.n_up = self.n_up + 1 if c > self.vah else 0
            self.n_dn = self.n_dn + 1 if c < self.val else 0
            width = self.vah - self.val
            width_ok = ((cfg.vaMinPoints <= 0 or width >= cfg.vaMinPoints)
                        and (cfg.vaMaxPoints <= 0 or width <= cfg.vaMaxPoints))
            if (width_ok and cfg.range_end <= cur < cfg.entry_end and pos == 0.0 and self.pending is None
                    and self.trades < int(cfg.maxTradesPerDay) and not out.close_session):
                need, buf = int(cfg.confirmCloses), int(cfg.slBufferTicks) * self.inst.tick_size
                retest = cfg.entryMode is EntryMode.RETEST
                go_long = (cfg.allowLong and self.n_up == need and (not cfg.useShape or self.shape_p) and (not cfg.useVwap or (vwap is not None and c > vwap)))
                go_short = (cfg.allowShort and self.n_dn == need and (not cfg.useShape or self.shape_b) and (not cfg.useVwap or (vwap is not None and c < vwap)))
                if go_long:
                    e, sl = (self.vah if retest else c), self.poc - buf
                    plan = self._plan(True, e, sl) if e > sl else None
                    if plan is not None:
                        self._enter(out, bar, idx, plan, f"{need}× zavretie nad VAH {self.inst.round_price(self.vah):g}"
                                    + (" — retest" if retest else ""), "nad VAH", limit=retest)
                elif go_short:
                    e, sl = (self.val if retest else c), self.poc + buf
                    plan = self._plan(False, e, sl) if e < sl else None
                    if plan is not None:
                        self._enter(out, bar, idx, plan, f"{need}× zavretie pod VAL {self.inst.round_price(self.val):g}"
                                    + (" — retest" if retest else ""), "pod VAL", limit=retest)
        self.prev_close = bar.close
        self.prev_min = cur
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
