"""Engine CRT + TBS: range sviečky vyššieho TF → výber jednej strany → otočka späť cez range.

Priebeh:

  1. **range** — každá uzavretá sviečka vyššieho TF (`rangeTF`, skladá sa z barov grafu) je
     kandidát: CRH = jej high, CRL = jej low (filtre veľkosti v ATR vyššieho TF, voliteľne
     „starý vrchol / dno" za `keyLookback` sviečok).
  2. **výber** — v nasledujúcich `sweepWithinBars` sviečkach vyššieho TF cena prekročí CRH
     (setup na short) alebo CRL (setup na long). `sweepKind=body` chce, aby za hranicou
     zavrela sviečka grafu (turtle body soup), `wick` stačí knôt. Výber oboch strán setup ruší.
  3. **vstup** — po výbere, keď je cena späť v rangu, prvý vstupný model na grafe:
       ``model1``  sviečka v smere obchodu zavrie za predošlou sviečkou
       ``cisd``    zavretie za otvorením posledného ťahu, ktorý spravil extrém výberu
       ``mss_fvg`` zavretie za posledným swingom s medzerou (FVG); limitka na hranu medzery
     Pri `requireHtfClose` až po tom, čo manipulačná sviečka vyššieho TF zavrela späť v rangu.
  4. **stop** za extrém výberu (+ rezerva v ATR a bodoch), **cieľ** stred rangu, opačný koniec
     alebo RR. Setup platí `validBars` sviečok vyššieho TF po range sviečke a končí vstupom,
     dosiahnutím cieľa bez vstupu alebo uplynutím.

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

from ..jss.engine import StructAggregator
from .config import CrtConfig, EntryModel, SweepKind, TpMode
from .drawing import CRT_ENTRY, CRT_MID, CRT_RANGE, CRT_SWEEP

__all__ = ["CrtEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_RANGE_COLOR = "#8b5cf6"
_RANGE_FILL = "#8b5cf61f"


@dataclass
class _Setup:
    """Jedna range sviečka a to, čo sa okolo nej deje."""

    uid: int
    high: float           #: CRH
    low: float            #: CRL
    start_ms: int         #: čas otvorenia range sviečky
    born: int             #: index sviečky vyššieho TF (range sviečka)
    direction: Direction | None = None   #: smer obchodu po výbere (None = ešte nebol)
    extreme: float = 0.0  #: extrém výberu (short: najvyšší high za CRH)
    body: bool = False    #: za hranicou zavrela sviečka grafu (TBS)
    sweep_idx: int = -1   #: index baru grafu prvého prekročenia hranice
    sweep_htf: int = -1   #: index sviečky vyššieho TF, v ktorej výber prišiel
    leg_open: float = 0.0  #: otvorenie posledného ťahu k extrému (CISD úroveň)
    htf_ok: bool = False  #: manipulačná sviečka vyššieho TF zavrela späť v rangu
    old: tuple[bool, bool] = (True, True)   #: ktorá strana je „starý" vrchol / dno (requireOldHL)

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2.0


class CrtEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: CrtConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        tf = int(cfg.rangeTF)
        if tf < self.chart_tf_minutes or tf % self.chart_tf_minutes:
            tf = -(-max(tf, self.chart_tf_minutes) // self.chart_tf_minutes) * self.chart_tf_minutes
        self.range_tf = tf
        self.agg = StructAggregator(tf, self.chart_tf_minutes)
        self.hbars: deque[Bar] = deque(maxlen=max(int(cfg.keyLookback) + 4, 16))
        self.h_idx = -1
        self.h_atr = 0.0
        self._h_seed: list[float] = []

        self.warmup = Warmup(self.chart_tf_minutes).add(
            f"ATR {cfg.atrLen} + swing {cfg.swingLen}", int(cfg.atrLen) + 2 * int(cfg.swingLen) + 40)
        self.warmup.add_seeded(f"range {tf}m", int(cfg.atrLen) + int(cfg.keyLookback) + 4, tf, self._seed)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self.required_history, 60) + 16, atr_len=int(cfg.atrLen))

        self.setups: list[_Setup] = []
        self._uid = 0
        self._zone = ZoneInfo(cfg.tradeTZ)
        self._pending: tuple[str, int, int] | None = None   # (order id, index baru, platí do indexu)
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._entry_idx = -1
        self._swing_low: float | None = None    #: posledný potvrdený swing grafu (pre MSS)
        self._swing_high: float | None = None

    # ------------------------------------------------------------------ #
    # vyšší TF
    # ------------------------------------------------------------------ #

    def _seed(self, bars, partial: Bar | None) -> None:
        for b in bars:
            self._htf_atr(b)
            self.hbars.append(b)
            self.h_idx += 1
        self.agg.prime(partial)

    def _htf_atr(self, b: Bar) -> None:
        prev = self.hbars[-1] if self.hbars else None
        tr = b.high - b.low if prev is None else max(b.high - b.low, abs(b.high - prev.close), abs(b.low - prev.close))
        if self.h_atr > 0:
            self.h_atr += (tr - self.h_atr) / int(self.cfg.atrLen)
        else:
            self._h_seed.append(tr)
            if len(self._h_seed) >= int(self.cfg.atrLen):
                self.h_atr = sum(self._h_seed) / len(self._h_seed)

    def _on_htf(self, b: Bar, out: EngineOutput) -> None:
        """Uzavretá sviečka vyššieho TF: uzavrie staré setupy a sama sa stane novým rangom."""
        cfg = self.cfg
        self._htf_atr(b)
        prior = list(self.hbars)
        self.hbars.append(b)
        self.h_idx += 1
        keep: list[_Setup] = []
        for s in self.setups:
            age = self.h_idx - s.born
            if s.direction is not None and s.sweep_htf == self.h_idx and not s.htf_ok:
                # manipulačná sviečka zavrela: späť v rangu?
                s.htf_ok = b.close < s.high if s.direction is Direction.SHORT else b.close > s.low
                if cfg.requireHtfClose and not s.htf_ok:
                    self._draw_range(out, s, b.time + self.agg.ms)
                    continue
            if (s.direction is None and age >= cfg.sweepWithinBars) or age >= cfg.validBars:
                self._draw_range(out, s, b.time + self.agg.ms)
                continue
            keep.append(s)
        self.setups = keep
        # nový range
        h = b.high - b.low
        atr = self.h_atr
        if h <= 0 or atr <= 0:
            return
        if h < cfg.rangeMinAtr.value * atr or (cfg.rangeMaxAtr.value > 0 and h > cfg.rangeMaxAtr.value * atr):
            return
        self._uid += 1
        s = _Setup(self._uid, b.high, b.low, b.time, self.h_idx)
        if cfg.requireOldHL:
            look = prior[-int(cfg.keyLookback):]
            s_old_high = bool(look) and b.high >= max(x.high for x in look)
            s_old_low = bool(look) and b.low <= min(x.low for x in look)
            if not (s_old_high or s_old_low):
                return
            # len tá strana, ktorá je starým extrémom, je likvidita hodná výberu
            s.old = (s_old_high, s_old_low)
        self.setups.append(s)

    # ------------------------------------------------------------------ #
    # kresby
    # ------------------------------------------------------------------ #

    def _draw_range(self, out: EngineOutput, s: _Setup, end_ms: int) -> None:
        if not self.cfg.showRanges or s.direction is None:
            return   # kreslia sa len rangy, na ktorých prišiel výber
        end_ms = max(end_ms, s.start_ms)
        out.drawings.append(DrawBox(CRT_RANGE, s.start_ms, s.high, end_ms, s.low, _RANGE_COLOR, _RANGE_FILL,
                                    obj_id=f"crt.range.{s.uid}", text=f"CRT {self.range_tf}m"))
        out.drawings.append(DrawLine(CRT_MID, s.start_ms, s.mid, end_ms, s.mid, _RANGE_COLOR, style=LineStyle.DASHED,
                                     obj_id=f"crt.mid.{s.uid}", text="50 %"))

    def _label(self, out: EngineOutput, kind, bar: Bar, text: str, long: bool, key: str) -> None:
        out.drawings.append(DrawLabel(
            kind, bar.time, bar.low if long else bar.high, text, "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"{key}.{bar.time}"))

    # ------------------------------------------------------------------ #
    # graf
    # ------------------------------------------------------------------ #

    def _update_swings(self) -> None:
        n = int(self.cfg.swingLen)
        if not self.history.has(2 * n + 1):
            return
        c = self.history[n]
        side = [self.history[i] for i in range(2 * n + 1) if i != n]
        if all(c.low < x.low for x in side):
            self._swing_low = c.low
        if all(c.high > x.high for x in side):
            self._swing_high = c.high

    def _leg_open(self, long: bool) -> float:
        """Otvorenie posledného ťahu k extrému: začiatok série sviečok proti smeru obchodu končiacej týmto barom."""
        k = 0
        while self.history.has(k + 2):
            b = self.history[k + 1]
            if (b.close < b.open) if long else (b.close > b.open):
                k += 1
            else:
                break
        return self.history[k].open

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        m = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= m < cfg.window_end_minutes

    def _track_sweep(self, s: _Setup, bar: Bar, idx: int, atr: float, out: EngineOutput) -> bool:
        """Aktualizuje výber na tomto bare; False = setup skončil (výber oboch strán / príliš hlboký)."""
        cfg = self.cfg
        above, below = bar.high > s.high, bar.low < s.low
        old = s.old
        if s.direction is None:
            if self.h_idx - s.born >= cfg.sweepWithinBars:
                return True   # čaká na uzavretie na ďalšej sviečke vyššieho TF
            if above and below:
                return False
            if above and old[0]:
                s.direction, s.extreme = Direction.SHORT, bar.high
            elif below and old[1]:
                s.direction, s.extreme = Direction.LONG, bar.low
            else:
                return not (above or below)
            s.sweep_idx, s.sweep_htf = idx, self.h_idx + 1
            s.leg_open = self._leg_open(long=s.direction is Direction.LONG)
            if cfg.showSweeps:
                self._label(out, CRT_SWEEP, bar, "TS", s.direction is Direction.LONG, f"crt.ts.{s.uid}")
        short = s.direction is Direction.SHORT
        if (short and below) or (not short and above):
            return False   # opačná strana rangu dosiahnutá bez vstupu — cieľ je preč
        if (short and bar.high > s.extreme) or (not short and bar.low < s.extreme) or idx == s.sweep_idx:
            s.extreme = max(s.extreme, bar.high) if short else min(s.extreme, bar.low)
            s.leg_open = self._leg_open(long=not short)
        if (bar.close > s.high) if short else (bar.close < s.low):
            s.body = True
        depth = cfg.sweepMaxAtr.value * atr
        if depth > 0 and abs(s.extreme - (s.high if short else s.low)) > depth:
            return False
        return True

    def _plan(self, s: _Setup, entry: float, atr: float) -> TradePlan | None:
        cfg = self.cfg
        long = s.direction is Direction.LONG
        buf = (cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
               + cfg.slBufferPoints.resolve(self.inst, price=entry, atr=atr))
        stop = s.extreme - buf if long else s.extreme + buf
        sl = entry - stop if long else stop - entry
        if sl < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl < min_sl:
            return None
        if cfg.tpMode is TpMode.RR:
            take = entry + sl * cfg.rrRatio if long else entry - sl * cfg.rrRatio
        else:
            take = s.mid if cfg.tpMode is TpMode.MID else (s.high if long else s.low)
            if (take - entry if long else entry - take) < sl * cfg.minRR:
                return None
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=s.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    def _signal(self, s: _Setup, bar: Bar) -> tuple[float, bool] | None:
        """Vstupný model na tomto bare: (cena vstupu, limitka?) alebo None."""
        cfg = self.cfg
        long = s.direction is Direction.LONG
        if not ((bar.close > s.low) if long else (bar.close < s.high)):
            return None   # cena ešte nie je späť v rangu
        if not self.history.has(3):
            return None
        prev, b2 = self.history[1], self.history[2]
        m = cfg.entryModel
        if m is EntryModel.MODEL1:
            ok = (bar.close > bar.open and bar.close > prev.high) if long else (bar.close < bar.open and bar.close < prev.low)
            return (bar.close, False) if ok else None
        if m is EntryModel.CISD:
            ok = bar.close > s.leg_open if long else bar.close < s.leg_open
            return (bar.close, False) if ok else None
        # MSS + FVG: zavretie za posledným swingom a medzera medzi 1. a 3. sviečkou
        level = self._swing_high if long else self._swing_low
        if level is None:
            return None
        if long and bar.close > level and bar.low > b2.high:
            return bar.low, True      # limitka na hornú hranu býčej medzery
        if not long and bar.close < level and bar.high < b2.low:
            return bar.high, True
        return None

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index
        self._update_swings()

        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        day = (local.year, local.month, local.day)
        if day != self._day:
            self._day = day
            self._trades_today = 0

        # ---- čakajúca limitka (mss_fvg) / pozícia ------------------------- #
        if self._pending is not None:
            if ctx.position_size != 0.0:
                self._trades_today += 1
                self._pending = None
            elif idx >= self._pending[2]:
                out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                              reason="limitka do medzery nevyplnená"))
                self._pending = None
        if cfg.maxHoldBars > 0 and ctx.position_size != 0.0 and self._entry_idx >= 0 \
                and idx - self._entry_idx >= cfg.maxHoldBars:
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                              reason=f"drží sa dlhšie než {cfg.maxHoldBars} barov"))
            self._entry_idx = -1

        # ---- výber a vstup na existujúcich setupoch ----------------------- #
        free = ctx.position_size == 0.0 and self._pending is None and atr > 0
        keep: list[_Setup] = []
        for s in self.setups:
            if not self._track_sweep(s, bar, idx, atr, out):
                self._draw_range(out, s, bar.time)
                continue
            keep.append(s)
            if s.direction is None or not free:
                continue
            long = s.direction is Direction.LONG
            if (long and not cfg.allow_long) or (not long and not cfg.allow_short):
                continue
            if cfg.sweepKind is SweepKind.BODY and not s.body:
                continue
            if cfg.requireHtfClose and not s.htf_ok:
                continue
            if idx <= s.sweep_idx and cfg.sweepKind is not SweepKind.WICK:
                continue
            if not self._in_window(bar) or self._trades_today >= cfg.maxTradesPerDay:
                continue
            sig = self._signal(s, bar)
            if sig is None:
                continue
            price, limit = sig
            plan = self._plan(s, price, atr)
            if plan is None:
                continue
            order_id = f"crt:{idx}"
            out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=s.direction, plan=plan,
                                          order_type=OrderType.LIMIT if limit else OrderType.MARKET,
                                          reason=f"CRT {self.range_tf}m + {cfg.entryModel.value}"))
            self._label(out, CRT_ENTRY, bar, f"{'LONG' if long else 'SHORT'} {cfg.entryModel.value}", long,
                        f"crt.e.{s.uid}")
            self._entry_idx = idx
            if limit:
                self._pending = (order_id, idx, idx + int(cfg.fvgValidBars))
            else:
                self._trades_today += 1
            free = False
            keep.remove(s)
            self._draw_range(out, s, bar.time)
        self.setups = keep

        # ---- vyšší TF: uzavretá sviečka je nový range ---------------------- #
        for hb in self.agg.push(bar):
            self._on_htf(hb, out)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        out = EngineOutput()
        for s in self.setups:
            self._draw_range(out, s, bar.time + self.step_ms)
        return list(out.drawings)
