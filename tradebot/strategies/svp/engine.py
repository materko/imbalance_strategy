"""Engine Volume Profile POC: seansový profil objemu a obchod na jeho POC.

Priebeh:

  1. **profil** — počas seansy (`sessionStart`–`sessionEnd`, America/New_York) sa objem každého
     baru grafu rovnomerne rozloží do cenových riadkov medzi jeho low a high (`rowTicks`).
     POC = stred riadku s najväčším objemom; value area = `valueAreaPct` % objemu okolo POC.
  2. **úroveň** — POC predošlej uzavretej seansy (`previous`, pevný celý deň) alebo vyvíjajúci sa
     POC dnešnej seansy (`developing`).
  3. **strana** — cena je „nad" / „pod" POC, keď bar zavrie aspoň `awayAtr` ATR od neho. Zmena
     strany zavretím aspoň `breakBufferAtr` za POC je **prerazenie**.
  4. **vstup** pri návrate k POC z tej strany, kde cena je (pod POC short, nad POC long):
       ``rejection`` mimo čerstvého prerazenia; ``retest`` len do `retestMaxBars` po prerazení; ``both`` oboje.
     ``touch`` = limitka na POC; inak sa po dotyku (do `touchTolAtr`) čaká `confirmBars` barov
     na IBS imbalance / pin bar v smere a vstupuje sa na zavretí. Po dotyku treba nový odchod.
  5. **stop** v ATR alebo bodoch od vstupu, **cieľ** RR alebo hrana value area.
  6. **Fibonacci** (`useFibo`): vstup len keď POC leží v pásme návratu poslednej nohy v smere obchodu
     (long: rastúca noha, short: klesajúca); stop sa dá dať za začiatok nohy, cieľ na jej extenziu.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawCommand, DrawLabel, DrawLine, LabelStyle, LineStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from ..fibo.legs import Leg, SwingLegs
from .config import EntryModel, PocSource, SlMode, SvpConfig, TpMode, TradeMode
from .drawing import SVP_ENTRY, SVP_FIB, SVP_POC, SVP_VA

__all__ = ["SvpEngine", "VolumeProfile"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_POC_COLOR = "#f59e0b"
_VA_COLOR = "#64748b"
_FIB_COLOR = "#eab308"
_NY = "America/New_York"


class VolumeProfile:
    """Objem po cenových riadkoch. Objem baru sa rovnomerne rozloží medzi jeho low a high."""

    def __init__(self, row: float) -> None:
        self.row = float(row)
        self.rows: dict[int, float] = {}
        self.total = 0.0

    def add(self, bar: Bar) -> None:
        if bar.volume <= 0 or self.row <= 0:
            return
        a, b = int(bar.low // self.row), int(bar.high // self.row)
        share = bar.volume / (b - a + 1)
        for k in range(a, b + 1):
            self.rows[k] = self.rows.get(k, 0.0) + share
        self.total += bar.volume

    def price(self, k: int) -> float:
        return (k + 0.5) * self.row

    @property
    def poc_row(self) -> int | None:
        if not self.rows:
            return None
        top = max(self.rows.values())
        best = [k for k, v in self.rows.items() if v == top]
        mid = (min(self.rows) + max(self.rows)) / 2.0
        return min(best, key=lambda k: abs(k - mid))   # pri zhode riadok bližší k stredu profilu

    @property
    def poc(self) -> float | None:
        k = self.poc_row
        return None if k is None else self.price(k)

    def value_area(self, pct: float) -> tuple[float, float] | None:
        """(VAL, VAH): od POC sa pridáva vždy ten susedný riadok, ktorý má väčší objem."""
        k = self.poc_row
        if k is None:
            return None
        lo = hi = k
        acc = self.rows[k]
        need = self.total * pct / 100.0
        kmin, kmax = min(self.rows), max(self.rows)
        while acc < need and (lo > kmin or hi < kmax):
            up = self.rows.get(hi + 1, 0.0) if hi < kmax else -1.0
            dn = self.rows.get(lo - 1, 0.0) if lo > kmin else -1.0
            if up >= dn:
                hi += 1; acc += max(up, 0.0)
            else:
                lo -= 1; acc += max(dn, 0.0)
        return lo * self.row, (hi + 1) * self.row


@dataclass
class _Pending:
    """Čakajúca limitka na POC."""

    order_id: str
    at: int              #: index baru, na ktorom bola zadaná
    price: float
    long: bool
    retest: bool
    leg: Leg | None      #: Fibonacciho noha, s ktorou POC sedí (kreslí sa pri vyplnení)


@dataclass
class _Level:
    poc: float
    val: float
    vah: float
    from_ms: int    #: odkedy úroveň platí (kreslenie)


class SvpEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: SvpConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.row = float(inst.tick_size) * int(cfg.rowTicks)
        self.zone = ZoneInfo(_NY)
        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrLen}", int(cfg.atrLen) + 8)
        self.legs: SwingLegs | None = None
        if cfg.useFibo:
            self.legs = SwingLegs(cfg.fibSwingTF, self.chart_tf_minutes, cfg.fibSwingLen, cfg.atrLen,
                                  cfg.fibLegMinAtr.value)
            self.warmup.add_seeded(f"fibo swingy {self.legs.tf}m", self.legs.seed_bars, self.legs.tf, self.legs.seed)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self.required_history, 8) + 16, atr_len=int(cfg.atrLen))

        self.profile: VolumeProfile | None = None     #: profil práve bežiacej seansy
        self.profile_day: tuple[int, int, int] | None = None
        self.prev: _Level | None = None               #: hotový profil predošlej seansy
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._side = 0            #: +1 cena je nad úrovňou, -1 pod, 0 ešte neodišla
        self._break_idx = -10**9  #: index baru posledného prerazenia úrovne
        self._armed = False       #: od posledného dotyku cena znova odišla — ďalší návrat je dotyk
        self._await: tuple[Direction, int] | None = None   #: po dotyku sa čaká na vstupný model (smer, do indexu)
        self._pending: _Pending | None = None
        self._drawn_from: int | None = None

    # ------------------------------------------------------------------ #

    def _level(self) -> _Level | None:
        """Úroveň, na ktorej sa práve obchoduje."""
        if self.cfg.pocSource is PocSource.PREVIOUS:
            return self.prev
        p = self.profile
        if p is None or p.poc is None:
            return None
        va = p.value_area(self.cfg.valueAreaPct)
        return _Level(p.poc, va[0], va[1], 0)

    def _finish_profile(self, out: EngineOutput, end_ms: int) -> None:
        p = self.profile
        self.profile = None
        if p is None or p.poc is None:
            return
        if self.prev is not None:
            self._draw_level(out, self.prev, end_ms)
        va = p.value_area(self.cfg.valueAreaPct)
        self.prev = _Level(p.poc, va[0], va[1], end_ms)
        if self.cfg.pocSource is PocSource.PREVIOUS:   # nová úroveň — strana a dotyky sa rátajú odznova
            self._side, self._armed, self._await, self._break_idx = 0, False, None, -10**9

    def _draw_level(self, out: EngineOutput, lv: _Level, end_ms: int) -> None:
        cfg = self.cfg
        if end_ms <= lv.from_ms:
            return
        if cfg.showPoc:
            out.drawings.append(DrawLine(SVP_POC, lv.from_ms, lv.poc, end_ms, lv.poc, _POC_COLOR, width=2,
                                         obj_id=f"svp.poc.{lv.from_ms}", text="POC"))
        if cfg.showValueArea:
            for name, y in (("VAH", lv.vah), ("VAL", lv.val)):
                out.drawings.append(DrawLine(SVP_VA, lv.from_ms, y, end_ms, y, _VA_COLOR, style=LineStyle.DASHED,
                                             obj_id=f"svp.{name}.{lv.from_ms}", text=name))

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

    def _fib(self, long: bool, price: float) -> tuple[bool, Leg | None]:
        """(smie sa obchodovať, noha): pri `useFibo` musí `price` (POC) ležať v pásme návratu nohy v smere obchodu."""
        if self.legs is None:
            return True, None
        leg = self.legs.legs.get(Direction.LONG if long else Direction.SHORT)
        if leg is None or leg.size <= 0:
            return False, None
        r = leg.retrace(price) * 100.0
        return self.cfg.fibMinPct - 1e-9 <= r <= self.cfg.fibMaxPct + 1e-9, leg

    def _draw_fib(self, out: EngineOutput, leg: Leg, end_ms: int) -> None:
        cfg = self.cfg
        if not cfg.showFibo:
            return
        out.drawings.append(DrawLine(SVP_FIB, leg.start_ms, leg.start, leg.end_ms, leg.end, _VA_COLOR,
                                     style=LineStyle.DASHED, obj_id=f"svp.fib.leg.{leg.uid}.{end_ms}", text="noha"))
        fracs = [0.0, cfg.fibMinPct / 100.0, cfg.fibMaxPct / 100.0, 1.0]
        if cfg.tpMode is TpMode.EXTENSION:
            fracs.append(-cfg.tpExtensionPct / 100.0)
        for f in fracs:
            y = leg.level(f)
            out.drawings.append(DrawLine(SVP_FIB, leg.end_ms, y, max(end_ms, leg.end_ms + self.step_ms), y, _FIB_COLOR,
                                         obj_id=f"svp.fib.{leg.uid}.{end_ms}.{f:g}", text=f"{f * 100:g} %"))

    def _plan(self, long: bool, entry: float, atr: float, lv: _Level, leg: Leg | None = None) -> TradePlan | None:
        cfg = self.cfg
        if cfg.slMode is SlMode.LEG:
            if leg is None:
                return None
            buf = cfg.slBufferAtr.value * atr
            sl = (entry - (leg.start - buf)) if long else ((leg.start + buf) - entry)
        else:
            sl = cfg.slAtr.value * atr if cfg.slMode is SlMode.ATR else cfg.slPoints.value
        if sl < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl < min_sl:
            return None
        stop = entry - sl if long else entry + sl
        if cfg.tpMode is TpMode.RR:
            take = entry + sl * cfg.rrRatio if long else entry - sl * cfg.rrRatio
        else:
            if cfg.tpMode is TpMode.EXTENSION:
                if leg is None:
                    return None
                take = leg.level(-cfg.tpExtensionPct / 100.0)
            else:
                take = lv.vah if long else lv.val
            if (take - entry if long else entry - take) < sl * cfg.minRR:
                return None
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    def _mode_ok(self, idx: int) -> bool:
        """Smie sa dotyk obchodovať? `retest` len do `retestMaxBars` po prerazení, `rejection` len mimo neho,
        `both` vždy."""
        m = self.cfg.tradeMode
        fresh = idx - self._break_idx <= int(self.cfg.retestMaxBars)
        if m is TradeMode.RETEST:
            return fresh
        if m is TradeMode.REJECTION:
            return not fresh
        return True

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index
        if self.legs is not None:
            self.legs.on_bar(bar)

        local = datetime.fromtimestamp(bar.time / 1000, tz=self.zone)
        day = (local.year, local.month, local.day)
        minutes = local.hour * 60 + local.minute
        if day != self._day:
            self._day = day
            self._trades_today = 0

        # ---- profil seansy -------------------------------------------------- #
        in_session = cfg.session_start <= minutes < cfg.session_end and local.weekday() < 5
        if self.profile is not None and (not in_session or self.profile_day != day):
            self._finish_profile(out, bar.time)
        if in_session:
            if self.profile is None:
                self.profile = VolumeProfile(self.row)
                self.profile_day = day
                if cfg.pocSource is PocSource.DEVELOPING:
                    self._side, self._armed, self._await, self._break_idx = 0, False, None, -10**9

        lv = self._level()   # úroveň známa PRED týmto barom (vyvíjajúci sa POC bez tohto baru)
        if in_session and self.profile is not None:
            self.profile.add(bar)

        # ---- čakajúca limitka / pozícia -------------------------------------- #
        if self._pending is not None:
            pe = self._pending
            long = pe.long
            # vyplnená: pozícia je otvorená, alebo cena limitkou prešla a obchod sa v tom istom bare aj zavrel
            if ctx.position_size != 0.0 or bar.low <= pe.price <= bar.high:
                self._trades_today += 1
                out.drawings.append(DrawLabel(
                    SVP_ENTRY, bar.time, bar.low if long else bar.high,
                    f"{'LONG' if long else 'SHORT'} {'retest' if pe.retest else 'POC'}", "#ffffff",
                    style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                    bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"svp.e.{bar.time}"))
                if pe.leg is not None:
                    self._draw_fib(out, pe.leg, bar.time)
                if ctx.position_size == 0.0:
                    out.orders.append(OrderIntent(OrderAction.CANCEL, pe.order_id, pe.at,
                                                  reason="vyplnené a zavreté v jednom bare"))
                self._pending = None
            elif idx - pe.at >= 1:
                out.orders.append(OrderIntent(OrderAction.CANCEL, pe.order_id, pe.at, reason="nevyplnené"))
                self._pending = None

        in_window = (not cfg.weekdaysOnly or local.weekday() < 5) and (
            not cfg.useTradeWindow or cfg.window_start_minutes <= minutes < cfg.window_end_minutes)
        if cfg.useTradeWindow and cfg.closeAtWindowEnd and minutes >= cfg.window_end_minutes and ctx.position_size != 0.0:
            out.close_session = True
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason="koniec okna obchodovania"))
            return out
        if lv is None or atr <= 0:
            return out

        L = lv.poc
        away = cfg.awayAtr.value * atr
        tol = cfg.touchTolAtr.value * atr
        brk = cfg.breakBufferAtr.value * atr

        # ---- dotyk z predošlého stavu (strana a „armed" sú z barov pred týmto) ---- #
        touched = None
        if self._armed and self._side != 0:
            if self._side < 0 and bar.high >= L - tol:
                touched = Direction.SHORT
            elif self._side > 0 and bar.low <= L + tol:
                touched = Direction.LONG
            if touched is not None:
                self._armed = False
                if cfg.entryModel is not EntryModel.TOUCH and self._mode_ok(idx):
                    self._await = (touched, idx + int(cfg.confirmBars) - 1)

        # ---- strana a prerazenie (zavretím) ---------------------------------- #
        prev_side = self._side
        if bar.close >= L + away:
            self._side = 1
        elif bar.close <= L - away:
            self._side = -1
        if prev_side != 0 and self._side != prev_side and abs(bar.close - L) >= brk:
            self._break_idx = idx      # POC prerazený zavretím — návrat k nemu je retest
            self._await = None
        # odchod: bar zavrel aspoň `awayAtr` od POC a sám sa ho nedotkol — až potom je návrat „dotyk"
        near = bar.low - tol <= L <= bar.high + tol
        if self._side != 0 and abs(bar.close - L) >= away and not near:
            self._armed = True

        free = ctx.position_size == 0.0 and self._pending is None and in_window \
            and self._trades_today < cfg.maxTradesPerDay
        if not free:
            if ctx.position_size != 0.0:
                self._await = None
            return out

        # ---- vstup ----------------------------------------------------------- #
        if cfg.entryModel is EntryModel.TOUCH:
            # limitka na POC platí na ďalší bar, kým je cena odídená a dotyk ešte nebol
            if self._armed and self._side != 0 and self._mode_ok(idx):
                long = self._side > 0
                ok, leg = self._fib(long, L)
                if ok and ((long and cfg.allow_long and bar.close > L) or (not long and cfg.allow_short and bar.close < L)):
                    self._enter(out, bar, idx, long, self.inst.round_price(L), atr, lv, limit=True, leg=leg)
            return out
        aw = self._await
        if aw is None:
            return out
        d, until = aw
        long = d is Direction.LONG
        if (long and bar.close < L - brk) or (not long and bar.close > L + brk):
            self._await = None       # POC prerazený zavretím — dotyk neplatí
            return out
        ok, leg = self._fib(long, L)
        if ok and self._signal(bar, long, atr) and ((long and cfg.allow_long) or (not long and cfg.allow_short)):
            self._await = None
            self._enter(out, bar, idx, long, bar.close, atr, lv, limit=False, leg=leg)
        elif idx >= until:
            self._await = None
        return out

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, long: bool, entry: float, atr: float, lv: _Level,
               limit: bool, leg: Leg | None = None) -> None:
        plan = self._plan(long, entry, atr, lv, leg)
        if plan is None:
            return
        order_id = f"{'svpL' if limit else 'svp'}:{idx}"
        retest = idx - self._break_idx <= int(self.cfg.retestMaxBars)
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.LIMIT if limit else OrderType.MARKET,
                                      reason=("retest POC po prerazení" if retest else "odmietnutie POC")))
        if limit:
            # nohu si limitka nesie ako kópiu — do vyplnenia sa živá noha môže predĺžiť alebo zaniknúť
            self._pending = _Pending(order_id, idx, plan.entry, long, retest, replace(leg) if leg is not None else None)
        else:
            self._trades_today += 1
            out.drawings.append(DrawLabel(
                SVP_ENTRY, bar.time, bar.low if long else bar.high,
                f"{'LONG' if long else 'SHORT'} {'retest' if retest else 'POC'}", "#ffffff",
                style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"svp.e.{bar.time}"))
            if leg is not None:
                self._draw_fib(out, leg, bar.time)

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        out = EngineOutput()
        if self.prev is not None:
            self._draw_level(out, self.prev, bar.time + self.step_ms)
        return list(out.drawings)
