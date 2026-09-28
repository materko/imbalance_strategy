"""Engine stratégie Drift VWAP Pullback: prvý návrat k VWAP v smere jeho sklonu.

Priebeh jedného obchodného dňa:

  1. VWAP sa počíta od kotvy (`vwapAnchor`, štandardne 9:30 New York) z 15m sviečok
     zložených z barov grafu (`vwapPeriod`), indikátor je `tradebot.core.vwap.SessionVwap`
  2. **drift** = zmena VWAP za posledných ``driftBars`` periód; kladný nad ``driftMinAtr`` × ATR
     je deň kupcov, záporný deň predajcov, medzi tým sa neobchoduje
     **smer dňa** = posledný jasný drift dňa; drží, kým sa VWAP jasne neotočí — počas
     pullbacku sa VWAP sploští a drift pod prah by inak zahodil práve ten dotyk
  3. cena musí **odísť** od VWAP — zavrieť aspoň ``awayAtr`` × ATR nad ním (long) alebo pod
     ním (short); tým je pohyb „ustálený" a návrat k VWAP je pullback. Odchod sa zaeviduje
     aj skôr, než má VWAP smer (z 15m je drift za 2 periódy známy až o 10:15)
  4. **pullback** = low baru (short: high) príde k VWAP bližšie než ``touchTolAtr`` × ATR.
     Počíta sa len dotyk, pri ktorom je smer dňa ten istý; pri ``firstPullbackOnly`` sa tým
     deň v tom smere končí — obchoduje sa len prvý
  5. vstup podľa ``entryMode``:
       ``limit`` limitka na VWAP (± tolerancia), leží od odchodu až do dotyku
       ostatné čakajú od dotyku najviac ``confirmBars`` barov na vstupnú sviečku:
       ``close`` bar, ktorý sa dotkne VWAP a zavrie späť na strane smeru (market na zavretí)
       ``stop``  stop order za prvý bar pullbacku, platí ``stopValidBars`` barov
       ``reaction`` / ``pinbar`` / ``engulfing`` market na zavretí prvej reakčnej sviečky
                 do protipohybu, pin baru, pohltenia
       pullback je prerazený, až keď bar zavrie za VWAP o viac než ``failCloseAtr`` × ATR
  6. stop podľa ``slMode`` (pullback / vstupná sviečka / VWAP / ATR od vstupu / swing), cieľ ``rrRatio`` × riziko
  7. na konci seansy sa pozícia zatvorí (``closeAtSessionEnd``)

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
from tradebot.core.vwap import SessionVwap
from tradebot.core.warmup import Warmup

from .config import EntryMode, SlMode, VwapDriftConfig
from .drawing import VD_ENTRY, VD_VWAP

__all__ = ["VwapDriftEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_FLAT_COLOR = "#94a3b8"
_NY = "America/New_York"


@dataclass
class _DayState:
    """Stav jedného obchodného dňa."""

    day: tuple[int, int, int] | None = None
    #: cena už odišla od VWAP v smere driftu — ďalší dotyk je pullback
    long_armed: bool = False
    short_armed: bool = False
    #: prvý pullback v tom smere už bol (obchodovaný alebo prerazený)
    long_done: bool = False
    short_done: bool = False
    trades: int = 0
    #: smer dňa — posledný jasný drift (+1 / -1), 0 kým VWAP smer nemal
    bias: int = 0

    def reset(self, day: tuple[int, int, int]) -> None:
        self.day = day
        self.bias = 0
        self.long_armed = self.short_armed = False
        self.long_done = self.short_done = False
        self.trades = 0


@dataclass
class _Pending:
    """Zadaný a ešte nevyplnený vstup (limit alebo stop)."""

    order_id: str
    direction: Direction
    kind: OrderType
    price: float
    #: posledný index baru, na ktorom smie ležať (stop); limit sa obnovuje každý bar
    until: int


@dataclass
class _Await:
    """Dotyk VWAP bol, čaká sa na potvrdzovaciu sviečku."""

    direction: Direction
    #: posledný index baru, na ktorom smie potvrdenie prísť
    until: int
    #: extrém pullbacku od dotyku (long najnižší low) — pre stop ``pullback``
    extreme: float


class VwapDriftEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: VwapDriftConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.zone = ZoneInfo(_NY)

        start, end, tz = cfg.vwapAnchor.window(cfg.start_minutes)
        self.vwap = SessionVwap(self.chart_tf_minutes, start_minutes=start, end_minutes=end,
                                tz=tz, period_minutes=cfg.vwapPeriod.minutes,
                                keep=int(cfg.driftBars) + 2)

        #: predhistória grafu: ATR a okno swingu — VWAP sa každý deň začína od nuly
        self.warmup = Warmup(self.chart_tf_minutes).add(
            f"ATR {cfg.atrLen}", int(cfg.atrLen) + 16).add(
            f"swing {cfg.slSwingBars}", int(cfg.slSwingBars))
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self.required_history, int(cfg.slSwingBars)) + 16,
                                  atr_len=int(cfg.atrLen))

        self._state = _DayState()
        self._pending: _Pending | None = None
        self._await: _Await | None = None
        #: posledný nakreslený bod čiary VWAP (čas, hodnota, deň) — úsečka sa kreslí z neho
        self._last_point: tuple[int, float, tuple[int, int, int] | None] | None = None

    # ------------------------------------------------------------------ #

    def drift(self, atr: float) -> int:
        """+1 VWAP stúpa, -1 klesá, 0 bez jasného smeru (alebo ešte málo periód)."""
        change = self.vwap.change(int(self.cfg.driftBars))
        if change is None or self.vwap.value is None:
            return 0
        thr = self.cfg.driftMinAtr.resolve(self.inst, price=self.vwap.value, atr=atr)
        if change > 0 and change >= thr:
            return 1
        if change < 0 and -change >= thr:
            return -1
        return 0

    def _stop(self, long: bool, entry: float, extreme: float, vwap: float, atr: float,
              candle: float) -> float:
        """Cena stopu podľa ``slMode``."""
        cfg = self.cfg
        buffer = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
        mode = cfg.slMode
        if mode is SlMode.ATR:
            dist = cfg.slAtr.resolve(self.inst, price=entry, atr=atr)
            return entry - dist if long else entry + dist
        if mode is SlMode.VWAP:
            base = vwap
        elif mode is SlMode.CANDLE:
            base = candle
        elif mode is SlMode.SWING:
            n = min(int(cfg.slSwingBars), len(self.history))
            bars = [self.history[i] for i in range(n)]
            base = min(b.low for b in bars) if long else max(b.high for b in bars)
        else:  # PULLBACK
            base = min(extreme, vwap) if long else max(extreme, vwap)
        return base - buffer if long else base + buffer

    def _plan(self, direction: Direction, entry: float, extreme: float, vwap: float,
              atr: float, candle: float | None = None) -> TradePlan | None:
        """Plán obchodu: stop podľa ``slMode``, cieľ ``rrRatio`` × vzdialenosť stopu."""
        cfg = self.cfg
        long = direction is Direction.LONG
        stop = self._stop(long, entry, extreme, vwap, atr, extreme if candle is None else candle)
        if (stop >= entry) if long else (stop <= entry):
            return None  # stop na zlej strane vstupu (napr. za VWAP pri vstupe pod ním)
        sl_distance = abs(entry - stop)
        if sl_distance < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl_distance < min_sl:
            return None
        take = entry + sl_distance * cfg.rrRatio if long else entry - sl_distance * cfg.rrRatio
        qty = (cfg.position_qty(self.inst, cfg.riskDollar, sl_distance)
               if cfg.riskDollar > 0 else 1.0)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(
            direction=direction, entry=self.inst.round_price(entry),
            stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
            qty=qty, sl_distance=sl_distance,
        )

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        st = self._state

        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index
        vwap = self.vwap.push(bar)

        local = datetime.fromtimestamp(bar.time / 1000, tz=self.zone)
        day = (local.year, local.month, local.day)
        if day != st.day:
            st.reset(day)
        minutes = local.hour * 60 + local.minute
        drift = self.drift(atr) if atr > 0 else 0
        if drift != 0 and self.vwap.day == st.day:
            st.bias = drift

        if cfg.showVwap and self.vwap.updated and vwap is not None:
            out.drawings += self._vwap_drawing(bar, vwap, drift)

        # ---- čakajúci limit / stop ------------------------------------- #
        pend = self._pending
        if pend is not None and ctx.position_size != 0.0:
            # vyplnený — sledovanie preberá adaptér; ráta sa ako obchod dňa
            self._pending = None
            st.trades += 1
            self._mark_done(pend.direction)
            out.drawings.append(self._entry_label(bar, pend.direction))
            pend = None

        tol = cfg.touchTolAtr.resolve(self.inst, price=bar.close, atr=atr) if atr > 0 else 0.0
        fail = cfg.failCloseAtr.resolve(self.inst, price=bar.close, atr=atr) if atr > 0 else 0.0
        if pend is not None and pend.kind is OrderType.STOP:
            long = pend.direction is Direction.LONG
            failed = vwap is not None and (bar.close < vwap - fail if long else bar.close > vwap + fail)
            if idx > pend.until or failed:
                self._cancel(out, idx, "stop vypršal" if idx > pend.until else "pullback prerazil VWAP")

        if cfg.weekdaysOnly and local.weekday() >= 5:
            return out

        # ---- koniec seansy --------------------------------------------- #
        if minutes >= cfg.end_minutes:
            self._await = None
            if self._pending is not None:
                self._cancel(out, idx, "koniec seansy")
            if cfg.closeAtSessionEnd and ctx.position_size != 0.0:
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                                  reason="koniec seansy"))
            return out
        if minutes < cfg.start_minutes or vwap is None or atr <= 0:
            return out

        # ---- odchod od VWAP v smere driftu ----------------------------- #
        away = cfg.awayAtr.resolve(self.inst, price=bar.close, atr=atr)
        if bar.close >= vwap + away and not st.long_done:
            st.long_armed = True
        if bar.close <= vwap - away and not st.short_done:
            st.short_armed = True

        # ---- pullback k VWAP ------------------------------------------- #
        touched: Direction | None = None
        # dotyk bez smeru dňa (alebo proti nemu) len zruší odchod — pullbackom nebol
        if st.long_armed and bar.low <= vwap + tol:
            st.long_armed = False
            if st.bias > 0:
                st.long_done = cfg.firstPullbackOnly
                touched = Direction.LONG
        if st.short_armed and bar.high >= vwap - tol:
            st.short_armed = False
            if st.bias < 0:
                st.short_done = cfg.firstPullbackOnly
                touched = Direction.SHORT if touched is None else None  # oba naraz = nejasné

        if self._pending is not None and self._pending.kind is OrderType.LIMIT:
            # limitka sa buď práve vyplnila (adaptér to povie na ďalšom bare), alebo jej
            # dôvod pominul — obnoví sa nižšie, ak ešte platí
            if touched is None:
                self._cancel(out, idx, "obnovenie limitky na VWAP", draw=False)

        can_enter = (ctx.position_size == 0.0 and self._pending is None
                     and st.trades < cfg.maxTradesPerDay and self._in_window(minutes))

        if cfg.entryMode is EntryMode.LIMIT:
            if can_enter:
                self._place_limit(out, idx, vwap, tol, drift, atr)
            return out
        self._confirm(out, idx, bar, touched, vwap, tol, fail, drift, atr, can_enter)
        return out

    # ------------------------------------------------------------------ #

    def _confirm(self, out: EngineOutput, idx: int, bar: Bar, touched: Direction | None,
                 vwap: float, tol: float, fail: float, drift: int, atr: float,
                 can_enter: bool) -> None:
        """Pullback od dotyku VWAP: najviac ``confirmBars`` barov sa čaká na vstupnú sviečku.

        Prvá, ktorá sedí na ``entryMode``, je vstup (market na jej zavretí, pri ``stop`` stop
        order za ňu). Pullback je prerazený, až keď bar zavrie za VWAP o viac než
        ``failCloseAtr`` — zavretie kúsok pod VWAP je stále pullback, nie jeho koniec.
        """
        cfg = self.cfg
        if touched is not None and self._await is None:
            extreme = bar.low if touched is Direction.LONG else bar.high
            self._await = _Await(touched, idx + int(cfg.confirmBars) - 1, extreme)
        aw = self._await
        if aw is None:
            return
        long = aw.direction is Direction.LONG
        aw.extreme = min(aw.extreme, bar.low) if long else max(aw.extreme, bar.high)
        if (bar.close < vwap - fail) if long else (bar.close > vwap + fail):
            self._await = None  # pullback prerazil VWAP
            return
        if self._pattern(bar, long, vwap, tol):
            self._await = None
            if not (can_enter and self._direction_ok(aw.direction, drift)):
                return
            candle = bar.low if long else bar.high
            if cfg.entryMode is EntryMode.STOP:
                tick = self.inst.tick_size or 0.0
                price = bar.high + tick if long else bar.low - tick
                self._enter(out, idx, bar, aw.direction, price, aw.extreme, vwap, atr,
                            OrderType.STOP, "pokračovanie po pullbacku k VWAP (stop)",
                            until=idx + int(cfg.stopValidBars), candle=candle)
            else:
                self._enter(out, idx, bar, aw.direction, bar.close, aw.extreme, vwap, atr,
                            OrderType.MARKET, f"pullback k VWAP ({cfg.entryMode.value})",
                            candle=candle)
            return
        if idx >= aw.until:
            self._await = None

    def _pattern(self, bar: Bar, long: bool, vwap: float, tol: float) -> bool:
        """Sedí bar na vstupnú sviečku zvoleného ``entryMode``?"""
        mode = self.cfg.entryMode
        bull, bear = bar.close > bar.open, bar.close < bar.open
        if mode is EntryMode.CLOSE:  # dotkne sa VWAP a zavrie späť na strane smeru
            if long:
                return bar.low <= vwap + tol and bar.close > vwap
            return bar.high >= vwap - tol and bar.close < vwap
        if mode is EntryMode.STOP:  # prvý bar pullbacku, ktorý ho neprerazil
            return True
        if mode is EntryMode.REACTION:
            return bull if long else bear
        if mode is EntryMode.PINBAR:
            rng = bar.high - bar.low
            if rng <= 0 or abs(bar.close - bar.open) > self.cfg.pbBodyPct / 100.0 * rng:
                return False
            wick = (min(bar.open, bar.close) - bar.low) if long else (bar.high - max(bar.open, bar.close))
            return wick >= self.cfg.pbWickPct / 100.0 * rng
        # ENGULFING: telo pohltí telo predošlej opačnej sviečky
        if not self.history.has(1):
            return False
        prev = self.history[1]
        if long:
            return bull and prev.close < prev.open and bar.close >= prev.open and bar.open <= prev.close
        return bear and prev.close > prev.open and bar.close <= prev.open and bar.open >= prev.close

    def _in_window(self, minutes: int) -> bool:
        since_open = minutes - self.cfg.start_minutes
        if since_open < self.cfg.entryDelayMinutes:
            return False
        return not (self.cfg.entryWindowMinutes > 0 and since_open > self.cfg.entryWindowMinutes)

    def _direction_ok(self, direction: Direction, drift: int) -> bool:
        """Smer je povolený a smer dňa (posledný jasný drift) je ten istý.

        ``drift`` je tu kvôli podpisu volaní; rozhoduje ``bias`` dňa, nie drift práve tohto
        baru — počas pullbacku sa VWAP sploští a prísny prah by zahodil práve ten dotyk,
        na ktorý stratégia čaká.
        """
        bias = self._state.bias
        if direction is Direction.LONG:
            return bias > 0 and self.cfg.allow_long
        return bias < 0 and self.cfg.allow_short

    def _mark_done(self, direction: Direction) -> None:
        if not self.cfg.firstPullbackOnly:
            return
        if direction is Direction.LONG:
            self._state.long_done, self._state.long_armed = True, False
        else:
            self._state.short_done, self._state.short_armed = True, False

    def _place_limit(self, out: EngineOutput, idx: int, vwap: float, tol: float, drift: int,
                     atr: float) -> None:
        """Limitka na VWAP (± tolerancia) v smere driftu, kým je cena odídená a dotyk nebol."""
        st = self._state
        if st.long_armed and self._direction_ok(Direction.LONG, drift):
            direction, price = Direction.LONG, vwap + tol
        elif st.short_armed and self._direction_ok(Direction.SHORT, drift):
            direction, price = Direction.SHORT, vwap - tol
        else:
            return
        plan = self._plan(direction, price, price, vwap, atr)
        if plan is None:
            return
        order_id = f"vd:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction,
                                      plan=plan, order_type=OrderType.LIMIT,
                                      reason="limitka na VWAP v smere driftu"))
        self._pending = _Pending(order_id, direction, OrderType.LIMIT, plan.entry, idx)

    def _enter(self, out: EngineOutput, idx: int, bar: Bar, direction: Direction, entry: float,
               extreme: float, vwap: float, atr: float, order_type: OrderType, reason: str,
               until: int | None = None, candle: float | None = None) -> None:
        plan = self._plan(direction, entry, extreme, vwap, atr, candle)
        if plan is None:
            return
        order_id = f"vd:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction,
                                      plan=plan, order_type=order_type, reason=reason))
        if order_type is OrderType.MARKET:
            self._state.trades += 1
            out.drawings.append(self._entry_label(bar, direction))
        else:
            self._pending = _Pending(order_id, direction, order_type, plan.entry,
                                     until if until is not None else idx)

    def _cancel(self, out: EngineOutput, idx: int, reason: str, draw: bool = True) -> None:
        pend = self._pending
        if pend is None:
            return
        out.orders.append(OrderIntent(OrderAction.CANCEL, pend.order_id, idx, reason=reason))
        self._pending = None

    def _entry_label(self, bar: Bar, direction: Direction) -> DrawLabel:
        long = direction is Direction.LONG
        return DrawLabel(
            VD_ENTRY, bar.time, bar.low if long else bar.high,
            "LONG" if long else "SHORT", "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR,
            obj_id=f"vd_entry.{bar.time}",
        )

    def _vwap_drawing(self, bar: Bar, vwap: float, drift: int) -> list[DrawCommand]:
        """Úsečka VWAP od posledného bodu; farba = drift (zelená hore, červená dole, sivá bez smeru).

        Bod je na **konci** baru, na ktorom sa hodnota zmenila — vtedy je známa. Nová seansa
        začína novú čiaru, s predošlým dňom sa nespája.
        """
        end_ms = bar.time + self.step_ms
        prev = self._last_point
        self._last_point = (end_ms, vwap, self.vwap.day)
        if prev is None or prev[2] != self.vwap.day:
            return []
        color = _LONG_COLOR if drift > 0 else _SHORT_COLOR if drift < 0 else _FLAT_COLOR
        return [DrawLine(VD_VWAP, prev[0], prev[1], end_ms, vwap, color,
                         obj_id=f"vd_vwap.{end_ms}", text="VWAP")]

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
