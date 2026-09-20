"""Engine stratégie Breakout: prerazenie prvej sviečky newyorského openu.

Priebeh jedného obchodného dňa:

  1. o otvorení seansy (9:30 New York) sa uzavrie **otváracia sviečka** — prvých
     ``openingMinutes`` minút; jej high a low sú jediné dve úrovne, na ktorých všetko stojí
  2. skontrolujú sa filtre šírky (``minRangePct`` / ``maxRangePct``)
  3. v obchodnom okne sa čaká, kým sviečka grafu **zavrie** nad high (long) alebo pod low
     (short) — samotné prepichnutie knôtom nestačí
  4. vstúpi sa podľa ``orderType``: ``market`` na zavretí prerazovacej sviečky, alebo
     ``limit`` späť na prerazenú hranicu (retest) s platnosťou ``limitValidMinutes``
  5. stop ide pod low (nad high) **otváracej** sviečky, cieľ je ``rrRatio`` × vzdialenosť stopu
  6. na konci seansy sa pozícia zatvorí (``closeAtSessionEnd``)

Otváracia sviečka neprichádza z barov grafu, ale z informatívneho TF (`htf.py`): 5 sa
dvomi ani tromi nedelí, takže na 3m grafe by z barov vyšlo okno 9:30–9:36. Takto vidia
1m, 2m aj 3m graf presne tú istú hranicu.

Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import BreakoutConfig, OrderKind
from .drawing import BO_BOX, BO_ENTRY, BO_HIGH, BO_LOW
from .htf import ClosedHtfBar

__all__ = ["BreakoutEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_RANGE_COLOR = "#f59e0b28"
_LEVEL_COLOR = "#f59e0bb3"

#: Zóna New Yorku, nie pevný posun: 9:30 NY je v zime 15:30 SEČ a v lete 15:30 SELČ,
#: a prechod na letný čas majú USA a Európa v iný týždeň. Pevný offset by tie dva
#: týždne v roku obchodoval o hodinu vedľa.
_NY = "America/New_York"


@dataclass
class _DayState:
    """Stav jedného obchodného dňa — jedna seansa, jedna otváracia sviečka."""

    day: tuple[int, int, int] | None = None
    high: float | None = None
    low: float | None = None
    open_ms: int = 0
    #: otváracia sviečka je zaevidovaná (a či prešla filtrom šírky)
    seen: bool = False
    ok: bool = False
    trades: int = 0

    def reset(self, day: tuple[int, int, int]) -> None:
        self.day = day
        self.high = None
        self.low = None
        self.open_ms = 0
        self.seen = False
        self.ok = False
        self.trades = 0


class BreakoutEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: BreakoutConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.zone = ZoneInfo(_NY)

        #: predhistória grafu: ATR a SMA objemu (seansa sa do nej nepočíta — `tradebot.core.warmup`)
        self.warmup = Warmup(self.chart_tf_minutes).add(
            f"ATR {cfg.atrLen} + SMA objemu {cfg.volSmaLen}",
            int(cfg.atrLen) + int(cfg.volSmaLen) + 16)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=self.required_history + 16, atr_len=int(cfg.atrLen))

        self._state = _DayState()
        #: zadaný a ešte nevyplnený vstupný order: (id, bar zadania, posledný platný bar)
        self._pending: tuple[str, int, int] | None = None
        #: koľko barov grafu je limitka v hre; market order sa plní hneď, tam je to 1
        self._limit_bars = max(1, round(cfg.limitValidMinutes / self.chart_tf_minutes))

    # ------------------------------------------------------------------ #
    # plán obchodu
    # ------------------------------------------------------------------ #

    def _plan(self, direction: Direction, entry: float, atr: float) -> TradePlan | None:
        """Plán obchodu: stop pod/nad **otváraciu** sviečku, cieľ ``rrRatio`` × vzdialenosť stopu."""
        cfg = self.cfg
        st = self._state
        if st.high is None or st.low is None:
            return None
        long = direction is Direction.LONG
        buffer = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
        stop = (st.low - buffer) if long else (st.high + buffer)

        sl_distance = abs(entry - stop)
        if sl_distance < self.inst.tick_size * 2:
            return None
        # Obchod s príliš tesným SL sa preskočí: poplatok je percento z nominálu a zisk
        # rastie s R, takže tesné stopy majú najhorší pomer edge k poplatku.
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl_distance < min_sl:
            return None

        take = entry + sl_distance * cfg.rrRatio if long else entry - sl_distance * cfg.rrRatio
        qty = (cfg.position_qty(self.inst, cfg.riskDollar, sl_distance)
               if cfg.riskDollar > 0 else 1.0)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)

        trailing = None
        if cfg.enableTrailing:
            act = sl_distance * cfg.trailActivationR
            off = sl_distance * cfg.trailOffsetR
            tick = self.inst.tick_size or 1.0
            trailing = TrailingPlan(
                activation_price_distance=act, offset_price_distance=off,
                activation_ticks=act / tick, offset_ticks=off / tick,
            )
        return TradePlan(
            direction=direction, entry=self.inst.round_price(entry),
            stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
            qty=qty, sl_distance=sl_distance, trailing=trailing,
        )

    # ------------------------------------------------------------------ #
    # filtre
    # ------------------------------------------------------------------ #

    def _width_ok(self, high: float, low: float, price: float) -> bool:
        """Šírka otváracej sviečky v percentách ceny — prah prenositeľný medzi trhmi."""
        if price <= 0:
            return False
        width_pct = (high - low) / price * 100.0
        return self.cfg.minRangePct <= width_pct <= self.cfg.maxRangePct

    def _volume_ok(self, bar: Bar) -> bool:
        if not self.cfg.useVolumeFilter:
            return True
        n = int(self.cfg.volSmaLen)
        if not self.history.has(n):
            return False
        avg = sum(self.history[i].volume for i in range(1, n + 1)) / n
        return avg > 0 and bar.volume >= avg * self.cfg.volMultiplier

    def _close_position_ok(self, bar: Bar, long: bool) -> bool:
        """Kde v rozpätí prerazovacej sviečky je jej close — 0 % = na minime, 100 % = na maxime."""
        span = bar.high - bar.low
        if span <= 0:
            return True
        pos = (bar.close - bar.low) / span * 100.0
        return pos >= self.cfg.minClosePosPct if long else (100.0 - pos) >= self.cfg.minClosePosPct

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf: ClosedHtfBar | None = None,
               ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        st = self._state

        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        # ---- nevyplnený vstupný order --------------------------------- #
        if ctx.position_size != 0.0:
            self._pending = None  # vyplnené — sledovanie preberá adaptér
        elif self._pending is not None and idx > self._pending[2]:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="limitka vypršala"))
            self._pending = None

        local = datetime.fromtimestamp(bar.time / 1000, tz=self.zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return out
        minutes = local.hour * 60 + local.minute

        day = (local.year, local.month, local.day)
        if day != st.day:
            st.reset(day)

        # ---- 1. otváracia sviečka z informatívneho TF ------------------ #
        if not st.seen and htf is not None:
            open_local = datetime.fromtimestamp(htf.open_ms / 1000, tz=self.zone)
            if (open_local.hour * 60 + open_local.minute == cfg.start_minutes
                    and (open_local.year, open_local.month, open_local.day) == day):
                st.seen = True
                st.high, st.low, st.open_ms = htf.bar.high, htf.bar.low, htf.open_ms
                st.ok = self._width_ok(st.high, st.low, htf.bar.close)
                out.drawings += self._range_drawings(bar, st, day)

        # ---- 6. koniec seansy ------------------------------------------ #
        if minutes >= cfg.end_minutes:
            if cfg.closeAtSessionEnd and ctx.position_size != 0.0:
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                                  reason="koniec seansy"))
            return out

        # ---- mantinely obchodného okna --------------------------------- #
        if not (st.seen and st.ok) or st.high is None or st.low is None:
            return out
        if minutes < cfg.start_minutes + cfg.openingMinutes.minutes:
            return out
        if cfg.entryWindowMinutes > 0 and minutes > cfg.start_minutes + cfg.entryWindowMinutes:
            return out
        if st.trades >= cfg.maxTradesPerDay:
            return out
        if ctx.position_size != 0.0 or self._pending is not None:
            return out

        # ---- 3. prerazenie: sviečka musí ZAVRIEŤ za hranicou ------------ #
        buffer = cfg.breakBufferAtr.resolve(self.inst, price=bar.close, atr=atr)
        long_break = cfg.allow_long and bar.close > st.high + buffer
        short_break = cfg.allow_short and bar.close < st.low - buffer
        if not (long_break or short_break):
            return out
        if not self._volume_ok(bar) or not self._close_position_ok(bar, long_break):
            return out

        # ---- 4. vstup: market na zavretí, alebo limitka na hranicu ------ #
        direction = Direction.LONG if long_break else Direction.SHORT
        if cfg.orderType is OrderKind.MARKET:
            entry, order_type = bar.close, OrderType.MARKET
            valid_until, reason = idx, "prerazenie (market)"
        else:
            entry, order_type = (st.high if long_break else st.low), OrderType.LIMIT
            valid_until = idx + self._limit_bars
            reason = "retest hranice (limit)"
        self._enter(out, direction, entry, atr, idx, valid_until, bar, order_type, reason)
        return out

    # ------------------------------------------------------------------ #

    def _range_drawings(self, bar: Bar, st: _DayState, day: tuple[int, int, int]) -> list[DrawCommand]:
        """Otváracia sviečka ako box a jej dve hranice — to, na čo sa celá stratégia pozerá."""
        cfg = self.cfg
        drawings: list[DrawCommand] = []
        if st.high is None or st.low is None:
            return drawings
        end_ms = st.open_ms + cfg.openingMinutes.minutes * 60_000
        if cfg.showRange:
            drawings.append(DrawBox(
                BO_BOX, st.open_ms, st.high, end_ms, st.low, _RANGE_COLOR,
                obj_id=f"bo.{day}", text=f"Otváracia sviečka {cfg.openingMinutes.minutes}m",
            ))
        if cfg.showLevels:
            right = bar.time + self.step_ms * 120
            drawings.append(DrawLine(BO_HIGH, end_ms, st.high, right, st.high, _LEVEL_COLOR,
                                     obj_id=f"boh.{day}", text="Open high"))
            drawings.append(DrawLine(BO_LOW, end_ms, st.low, right, st.low, _LEVEL_COLOR,
                                     obj_id=f"bol.{day}", text="Open low"))
        return drawings

    def _enter(self, out: EngineOutput, direction: Direction, entry: float, atr: float,
               idx: int, valid_until: int, bar: Bar, order_type: OrderType, reason: str) -> None:
        plan = self._plan(direction, entry, atr)
        if plan is None:
            return
        order_id = f"bo:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction,
                                      plan=plan, order_type=order_type, reason=reason))
        self._pending = (order_id, idx, valid_until)
        # Počíta sa pokus o vstup, nie vyplnený obchod: či sa limitka vráti k hranici,
        # engine na bare zadania nevie a `maxTradesPerDay` má byť strop na deň, nie
        # skrytý filter dní, v ktorých sa nevyplnilo.
        self._state.trades += 1
        long = direction is Direction.LONG
        out.drawings.append(DrawLabel(
            BO_ENTRY, bar.time, bar.low if long else bar.high,
            "LONG" if long else "SHORT", "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR,
            obj_id=f"bo_entry.{bar.time}",
        ))

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
