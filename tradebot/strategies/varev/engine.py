"""Engine VALUE AREA REVERSION 1.0: únik z value area so slabnúcim objemom a návrat dnu so silným objemom.

Priebeh na každom uzavretom bare grafu (`_update` — to isté aj pre predhistóriu pred behom):

  1. **seansa** — začína o `anchorH` (18:00 New York), pri `profileSession` ny je to len NY seansa 9:30–16:00 (bary
     mimo nej do profilu nejdú). Bary seansy sa zbierajú do profilu; na konci seansy sa z neho
     spočíta POC a value area (`_Profile.levels`) — to je profil „previous“ pre celú ďalšiu seansu. Pri „current“ sa
     value area počíta z barov dnešnej seansy pred aktuálnym barom (bez pohľadu na bar, o ktorom sa rozhoduje),
  2. **únik** — zavretie pod VAL (nad VAH), keď predošlé zavretie ešte nebolo pod VAL (nad VAH); od neho sa sleduje
     extrém a objemy sviečok v smere úniku,
  3. **návrat** — najviac `maxBarsOutside` barov po úniku zavrie sviečka späť vo value area; signál, keď je v smere
     obchodu, objem únikových sviečok klesal a návrat má väčší objem ako posledná úniková sviečka. Návrat bez
     splnených podmienok únik ukončí bez obchodu,
  4. **vstup** market na zavretí, stop za extrém úniku, cieľ opačná hrana value area / POC / RR.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawCommand, DrawLabel, DrawLine, LabelStyle, LineStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import ProfileSession, ProfileSource, TpMode, VaRevConfig
from .drawing import VR_ESCAPE, VR_POC, VR_SIGNAL, VR_VAH, VR_VAL

__all__ = ["VaRevEngine", "value_area"]

NY = ZoneInfo("America/New_York")
LONG_COLOR, SHORT_COLOR = "#10b981", "#ef4444"
VAH_COLOR, VAL_COLOR, POC_COLOR = "#089981", "#f23645", "#5b9cf6"


def value_area(bars: list[tuple[float, float, float]], rows: int, pct: float) -> tuple[float, float, float] | None:
    """(VAH, VAL, POC) profilu z barov (high, low, objem); objem baru sa rozdelí rovnomerne do riadkov, ktorých sa
    dotkol. Value area rastie od POC k väčšiemu zo susedných riadkov (pri zhode hore), kým nemá `pct` % objemu."""
    if not bars:
        return None
    lo = min(b[1] for b in bars)
    hi = max(b[0] for b in bars)
    total = sum(b[2] for b in bars)
    if hi <= lo or total <= 0:
        return None
    step = (hi - lo) / rows
    vol = [0.0] * rows
    for h, l, v in bars:
        if v <= 0:
            continue
        i0 = min(rows - 1, max(0, int((l - lo) / step)))
        i1 = min(rows - 1, max(0, int((h - lo) / step)))
        per = v / (i1 - i0 + 1)
        for i in range(i0, i1 + 1):
            vol[i] += per
    poc = max(range(rows), key=lambda i: (vol[i], -i))   # prvý najväčší zdola
    target = total * pct / 100.0
    acc, up, dn = vol[poc], poc, poc
    while acc < target and (up < rows - 1 or dn > 0):
        above = vol[up + 1] if up < rows - 1 else -1.0
        below = vol[dn - 1] if dn > 0 else -1.0
        if above >= below:
            up += 1
            acc += above
        else:
            dn -= 1
            acc += below
    return lo + (up + 1) * step, lo + dn * step, lo + (poc + 0.5) * step


@dataclass
class _Escape:
    direction: Direction    #: smer obchodu (únik pod VAL → long)
    start: int
    extreme: float
    vols: list[float] = field(default_factory=list)   #: objemy sviečok v smere úniku


class VaRevEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: VaRevConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        self.history = BarHistory(maxlen=int(cfg.atrLen) + 8, atr_len=int(cfg.atrLen))
        self.idx = -1
        self._sess = None
        self._sess_start_ms = 0
        self._bars: list[tuple[float, float, float]] = []      # bary dnešnej seansy (high, low, objem)
        self.prev_levels: tuple[float, float, float] | None = None
        self.levels: tuple[float, float, float] | None = None  # (VAH, VAL, POC) platné pre aktuálny bar
        self._prev_close: float | None = None
        self.escape: _Escape | None = None
        self._seg: list | None = None                           # kreslený úsek čiar value area
        self._trade_day = None
        self._trades_today = 0
        # predhistória: celá predošlá seansa (+ rezerva na víkend / sviatok)
        self.warmup = Warmup(self.tf).add_seeded("profil predošlej seansy", 4 * 1440 // self.tf, self.tf, self._seed)
        self.required_history = self.warmup.chart_bars

    # ------------------------------------------------------------------ #

    def _seed(self, closed: list[Bar], partial: Bar | None) -> None:
        for bar in closed:
            self._update(bar, None)

    def _session_key(self, t_ms: int):
        local = datetime.fromtimestamp(t_ms / 1000, tz=NY) - timedelta(hours=int(self.cfg.anchorH))
        return local.date()

    def _close_segment(self, end_ms: int, out: EngineOutput | None) -> None:
        seg, self._seg = self._seg, None
        cfg = self.cfg
        if seg is None or out is None or not cfg.showValueArea:
            return
        start, (vah, val, poc) = seg
        if end_ms <= start:
            return
        out.drawings.append(DrawLine(VR_VAH, start, vah, end_ms, vah, VAH_COLOR, obj_id=f"vr.vah.{start}", text="VAH"))
        out.drawings.append(DrawLine(VR_VAL, start, val, end_ms, val, VAL_COLOR, obj_id=f"vr.val.{start}", text="VAL"))
        if cfg.showPoc:
            out.drawings.append(DrawLine(VR_POC, start, poc, end_ms, poc, POC_COLOR, style=LineStyle.DASHED,
                                         obj_id=f"vr.poc.{start}", text="POC"))

    def _update(self, bar: Bar, out: EngineOutput | None) -> Direction | None:
        """Stav po uzavretí baru; vráti smer signálu (návrat do value area so splnenými podmienkami)."""
        cfg = self.cfg
        self.idx += 1
        idx = self.idx
        self.history.append(bar)
        # seansa profilu: globex 18:00–18:00, alebo len NY seansa (bar patrí do nej podľa času otvorenia);
        # profil sa uzavrie na prvom bare mimo svojej seansy — od neho platí ako „previous“
        if cfg.profileSession is ProfileSession.NY:
            local = datetime.fromtimestamp(bar.time / 1000, tz=NY)
            m = local.hour * 60 + local.minute
            in_profile = cfg.nyStartH * 60 + cfg.nyStartM <= m < cfg.nyEndH * 60 + cfg.nyEndM
            key = local.date() if in_profile else None
        else:
            in_profile, key = True, self._session_key(bar.time)
        if key != self._sess:
            if self._sess is not None:
                self.prev_levels = value_area(self._bars, int(cfg.profileRows), float(cfg.valueAreaPct))
                self.escape = None
            self._sess, self._sess_start_ms, self._bars = key, bar.time, []
        # value area pre tento bar: predošlá seansa, alebo dnešná z barov pred týmto
        if cfg.profileSource is ProfileSource.CURRENT:
            levels = value_area(self._bars, int(cfg.profileRows), float(cfg.valueAreaPct))
        else:
            levels = self.prev_levels
        if in_profile:
            self._bars.append((bar.high, bar.low, max(0.0, float(bar.volume))))
        if levels != (self._seg[1] if self._seg else None):
            self._close_segment(bar.time, out)
            if levels is not None:
                self._seg = [bar.time, levels]
        self.levels = levels
        prev_close, self._prev_close = self._prev_close, bar.close
        if levels is None:
            self.escape = None
            return None
        vah, val, _ = levels
        bull, bear = bar.close > bar.open, bar.close < bar.open
        signal: Direction | None = None

        e = self.escape
        if e is not None and idx > e.start:
            long = e.direction is Direction.LONG
            inside = val < bar.close <= vah if long else val <= bar.close < vah
            if inside:
                self.escape = None
                ok = bull if long else bear
                if cfg.requireVolDecline:
                    ok = ok and len(e.vols) >= 2 and e.vols[-1] < e.vols[-2]
                if cfg.reclaimVolMult > 0:
                    ok = ok and bool(e.vols) and bar.volume > e.vols[-1] * cfg.reclaimVolMult
                if cfg.requireEngulf and self.history.has(2):
                    p = self.history[1]
                    ok = ok and (bar.close >= max(p.open, p.close) and bar.open <= min(p.open, p.close) if long
                                 else bar.close <= min(p.open, p.close) and bar.open >= max(p.open, p.close))
                if ok:
                    signal = e.direction
            elif (long and bar.close > vah) or (not long and bar.close < val):
                self.escape = None                       # preletela celú value area — nie návrat
            elif idx - e.start >= int(cfg.maxBarsOutside):
                self.escape = None                       # návrat neprišiel včas
            else:
                e.extreme = min(e.extreme, bar.low) if long else max(e.extreme, bar.high)
                if (bear if long else bull):
                    e.vols.append(float(bar.volume))
            if signal is not None or self.escape is not None:
                return signal

        # nový únik: zavretie za hranou, predošlé zavretie ešte nie
        if bar.close < val and (prev_close is None or prev_close >= val):
            self.escape = _Escape(Direction.LONG, idx, bar.low, [float(bar.volume)] if bear else [])
        elif bar.close > vah and (prev_close is None or prev_close <= vah):
            self.escape = _Escape(Direction.SHORT, idx, bar.high, [float(bar.volume)] if bull else [])
        else:
            return None
        if out is not None and cfg.showSignals:
            long = self.escape.direction is Direction.LONG
            out.drawings.append(DrawLabel(VR_ESCAPE, bar.time, bar.low if long else bar.high, "únik", "#94a3b8",
                                          style=LabelStyle.NONE, above=not long, obj_id=f"vr.esc.{bar.time}"))
        return None

    def _plan(self, d: Direction, bar: Bar, extreme: float) -> TradePlan | None:
        cfg = self.cfg
        long = d is Direction.LONG
        atr = self.history.atr
        entry = bar.close
        buf = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr) if atr > 0 else 0.0
        stop = extreme - buf if long else extreme + buf
        sl = abs(entry - stop)
        if sl < self.inst.tick_size * 2 or (long and stop >= entry) or (not long and stop <= entry):
            return None
        vah, val, poc = self.levels
        if cfg.tpMode is TpMode.RR:
            take = entry + cfg.rrRatio * sl if long else entry - cfg.rrRatio * sl
        else:
            take = (vah if long else val) if cfg.tpMode is TpMode.VA else poc
        dist = take - entry if long else entry - take
        if dist < self.inst.tick_size * 2 or (cfg.minRR > 0 and dist < cfg.minRR * sl):
            return None
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        return TradePlan(direction=d, entry=self.inst.round_price(entry), stop_loss=self.inst.round_price(stop),
                         take_profit=self.inst.round_price(take), qty=qty if qty > 0 else 1.0, sl_distance=sl)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        cfg, out = self.cfg, EngineOutput()
        esc = self.escape
        extreme = None if esc is None else min(esc.extreme, bar.low) if esc.direction is Direction.LONG \
            else max(esc.extreme, bar.high)
        d = self._update(bar, out)
        t = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
        m, day = t.hour * 60 + t.minute, (t.year, t.month, t.day)
        if day != self._trade_day:
            self._trade_day, self._trades_today = day, 0
        if d is None or extreme is None or ctx.position_size != 0.0:
            return out                                   # kým beží obchod, nové signály sa neberú
        long = d is Direction.LONG
        if (long and not cfg.allow_long) or (not long and not cfg.allow_short):
            return out
        if self._trades_today >= int(cfg.maxTradesPerDay) or (cfg.weekdaysOnly and t.weekday() >= 5):
            return out
        if cfg.useTradeWindow:
            start, end = cfg.window
            if not (start < m <= end):
                return out
        plan = self._plan(d, bar, extreme)
        if plan is None:
            return out
        self._trades_today += 1
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"vr:{self.idx}", self.idx, direction=d, plan=plan,
                                      order_type=OrderType.MARKET, reason="návrat do value area so silným objemom"))
        if cfg.showSignals:
            out.drawings.append(DrawLabel(VR_SIGNAL, bar.time, bar.low if long else bar.high,
                                          "VA ▲" if long else "VA ▼", "#ffffff",
                                          style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                          bg_color=LONG_COLOR if long else SHORT_COLOR, obj_id=f"vr.sig.{bar.time}"))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        out = EngineOutput()
        self._close_segment(bar.time + self.step_ms, out)
        return list(out.drawings)
