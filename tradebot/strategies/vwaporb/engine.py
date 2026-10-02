"""Engine VWAP ORB 1.0: ORB, v ktorom je prerazenie signálom až keď je za rangom aj VWAP.

Celý ORB (stavanie rangu, stop, cieľ, koniec seansy, kresby) je `ORBEngine`; tento engine
k nemu pridáva seansový VWAP (`tradebot.core.vwap.SessionVwap`) a podmienku cez háčik
`_break_allowed`:

* **long** — close nad high rangu (to kontroluje ORB) **a** podľa ``vwapRule``:
  ``break`` VWAP nad high rangu (o ``vwapBreakAtr`` × ATR), ``direction`` VWAP stúpa
  (zmena za ``vwapDriftBars`` periód aspoň ``vwapDriftMinAtr`` × ATR);
  pri ``closeBeyondVwap`` navyše close nad VWAP
* **short** — zrkadlovo pod low

Stop na VWAP (``vwapStop``): počiatočný stop je VWAP pri signáli (± ``vwapStopAtr`` × ATR),
potom sa posúva s VWAP (`trailing.VwapTrailing`) a obchod končí dotykom VWAP. Keď je VWAP pri
signáli na zlej strane vstupu (pri ``vwapRule=direction`` sa to stáva), platí stop ORB
a s VWAP sa posunie, až keď VWAP prejde na správnu stranu.

TP na cross VWAP (``vwapTp``): stop ostáva ORB; keď je VWAP za vstupom v zisku, stop ide na
VWAP a jeho dotyk obchod zavrie so ziskom. Pri zapnutom ``vwapStop`` sa nepoužije.

Výstup (``exitMode``): ``tp`` je cieľ ORB; ``vwap`` drží obchod bez cieľa, kým cena od vstupu
neprerazí VWAP proti nemu — bola na správnej strane a zavrie na opačnej (o ``vwapExitAtr`` × ATR);
``tp_vwap`` čo príde skôr.

ORB hodnotí prerazenie na každom bare obchodného okna, kým nepadne obchod — vstup je teda
na zavretí **prvej** sviečky, na ktorej platí oboje, aj keď VWAP za range dôjde až hodinu
po tom, čo ho prerazila cena.
"""

from __future__ import annotations

from tradebot.core.drawing import DrawCommand, DrawLine
from tradebot.core.engine import EngineOutput
from dataclasses import replace

from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec
from tradebot.core.vwap import SessionVwap

from ..orb.engine import ORBEngine
from .config import EntryTiming, ExitMode, VwapOrbConfig, VwapRule
from .drawing import VO_VWAP
from .trailing import VwapSeries, VwapTrailing

__all__ = ["VwapOrbEngine"]

_VWAP_COLOR = "#a855f7"

#: Cieľ pri ``exitMode=vwap`` — ďaleko, aby ho cena prakticky nedosiahla (adaptéry TP potrebujú).
_NO_TP_R = 100.0


class VwapOrbEngine(ORBEngine):
    """ORB + VWAP. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: VwapOrbConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        super().__init__(cfg, inst, chart_tf_minutes)
        start, end, tz = cfg.vwapAnchor.window(cfg.nyStartH * 60 + cfg.nyStartM)
        self.vwap = SessionVwap(self.chart_tf_minutes, start_minutes=start, end_minutes=end,
                                tz=tz, period_minutes=cfg.vwapPeriod.minutes,
                                keep=int(cfg.vwapDriftBars) + 2)
        #: VWAP z barov grafu — smer pri ``break_candle``, keď 15m VWAP ešte nemá ani jednu periódu
        per = cfg.vwapPeriod.minutes
        self._fast_bars = max(1, int(cfg.vwapDriftBars) * (per // self.chart_tf_minutes if per else 1))
        self.vwap_fast = SessionVwap(self.chart_tf_minutes, start_minutes=start, end_minutes=end,
                                     tz=tz, keep=self._fast_bars + 2)
        #: VWAP v čase (kedy bola hodnota známa) — pre stop na VWAP
        self._series = VwapSeries()
        #: smery, v ktorých už dnes prerazovacia sviečka bola: (deň, smer)
        self._broke: set[tuple] = set()
        self._vwap_value: float | None = None
        #: pozícia už bola na správnej strane VWAP — ďalšie zavretie za ním proti obchodu ju zatvorí
        self._exit_ready = False
        #: posledný nakreslený bod čiary VWAP (čas, hodnota, deň)
        self._vwap_point: tuple[int, float, tuple[int, int, int] | None] | None = None

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        # VWAP pred ORB: podmienka prerazenia sa pýta na hodnotu po zavretí tohto baru
        ctx = ctx or MarketContext(in_trade_window=True)
        # Mimo seansy VWAP (napr. Londýn pri kotve 9:30 NY) by `push` vrátil včerajšiu zamrznutú hodnotu —
        # tá nie je dnešný VWAP, takže sa podľa nej nevstupuje, nestopuje ani nevystupuje.
        value = self.vwap.push(bar)
        self._vwap_value = value if self.vwap.live else None
        self.vwap_fast.push(bar)
        if self._vwap_value is not None:
            self._series.add(bar.time + self.step_ms, self._vwap_value, bar.close)
        out = super().on_bar(bar, htf, ctx)
        if self.cfg.showVwap and self.vwap.updated and self._vwap_value is not None:
            out.drawings += self._vwap_drawing(bar, self._vwap_value)
        if self.cfg.exitMode.vwap_exit:
            self._vwap_exit(out, bar, ctx)
        return out

    def _vwap_exit(self, out: EngineOutput, bar: Bar, ctx: MarketContext) -> None:
        """Zavrie pozíciu, keď cena od vstupu prerazí VWAP proti obchodu.

        Prerazenie = pozícia bola na správnej strane VWAP (long nad ním) a bar zavrie na opačnej
        o ``vwapExitAtr`` × ATR. Signálny bar sa počíta tiež: vstup nad VWAP je už na správnej strane.
        """
        vwap = self._vwap_value
        pos = ctx.position_size
        entry = next((o for o in out.orders if o.action is OrderAction.ENTRY), None)
        if pos == 0.0:
            # nová pozícia z tohto baru: pripravená, ak signálny bar zavrel na správnej strane
            long = entry is not None and entry.direction is Direction.LONG
            self._exit_ready = (entry is not None and vwap is not None
                                and ((bar.close > vwap) if long else (bar.close < vwap)))
            return
        if vwap is None or out.close_session:
            return
        long = pos > 0.0
        buffer = self.cfg.vwapExitAtr.resolve(self.inst, price=bar.close, atr=self.history.atr)
        if (bar.close > vwap) if long else (bar.close < vwap):
            self._exit_ready = True
            return
        wrong = (bar.close < vwap - buffer) if long else (bar.close > vwap + buffer)
        if self._exit_ready and wrong:
            out.close_session = True
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, self.history.bar_index,
                                              reason="prerazenie VWAP proti obchodu"))
            self._open_session = None
            self._exit_ready = False

    def _stop_level(self, st, direction: Direction, entry: float, atr: float) -> float | None:
        """Pri ``vwapStop`` stop na VWAP, ak je VWAP na správnej strane vstupu; inak stop ORB."""
        vwap = self._vwap_value
        if self.cfg.vwapStop and vwap is not None:
            buffer = self.cfg.vwapStopAtr.resolve(self.inst, price=entry, atr=atr)
            stop = vwap - buffer if direction is Direction.LONG else vwap + buffer
            if (stop < entry) if direction is Direction.LONG else (stop > entry):
                return stop
        return super()._stop_level(st, direction, entry, atr)

    def _plan(self, st, direction: Direction, entry: float, atr: float) -> TradePlan | None:
        plan = super()._plan(st, direction, entry, atr)
        cfg = self.cfg
        if plan is None or not (cfg.vwapStop or cfg.vwapTp):
            return plan
        if cfg.vwapStop:  # stop na VWAP pokrýva aj TP na cross — je prísnejší
            buffer = cfg.vwapStopAtr.resolve(self.inst, price=entry, atr=atr)
            return replace(plan, trailing=VwapTrailing.following(self._series, buffer))
        buffer = cfg.vwapTpAtr.resolve(self.inst, price=entry, atr=atr)
        return replace(plan, trailing=VwapTrailing.following(self._series, buffer, profit_only=True))

    def _target_level(self, st, direction: Direction, entry: float, sl_distance: float,
                      atr: float) -> float:
        """Pri ``exitMode=vwap`` bez pevného cieľa — cieľ 100R, inak cieľ ORB."""
        if self.cfg.exitMode is ExitMode.VWAP:
            dist = sl_distance * _NO_TP_R
            if direction is Direction.LONG:
                return entry + dist
            return max(entry - dist, entry * 0.01)
        return super()._target_level(st, direction, entry, sl_distance, atr)

    def _break_allowed(self, st, direction: Direction, bar: Bar, atr: float) -> bool:
        """VWAP podľa ``vwapRule`` v smere prerazenia (a pri ``closeBeyondVwap`` aj cena za VWAP)."""
        vwap = self._vwap_value
        if vwap is None or st.high is None or st.low is None:
            return False
        cfg = self.cfg
        long = direction is Direction.LONG
        candle_only = cfg.entryTiming is EntryTiming.BREAK_CANDLE
        if candle_only:
            # ORB sa pýta len pri close za rangom — prvé opýtanie v smere je prerazovacia sviečka
            key = (st.day, direction)
            if key in self._broke:
                return False
            self._broke.add(key)
        if cfg.closeBeyondVwap and not ((bar.close > vwap) if long else (bar.close < vwap)):
            return False
        if cfg.vwapRule is VwapRule.DIRECTION:
            change = self._vwap_change(int(cfg.vwapDriftBars), fallback=candle_only)
            if change is None:
                return False
            need = cfg.vwapDriftMinAtr.resolve(self.inst, price=vwap, atr=atr)
            return change > 0 and change >= need if long else change < 0 and -change >= need
        need = cfg.vwapBreakAtr.resolve(self.inst, price=bar.close, atr=atr)
        return vwap > st.high + need if long else vwap < st.low - need

    def _vwap_change(self, bars: int, fallback: bool) -> float | None:
        """Zmena VWAP za ``bars`` periód; pri ``fallback`` aj za menej periód, alebo z barov grafu."""
        change = self.vwap.change(bars)
        if change is not None or not fallback:
            return change
        for n in range(bars - 1, 0, -1):
            change = self.vwap.change(n)
            if change is not None:
                return change
        for n in range(self._fast_bars, 0, -1):
            change = self.vwap_fast.change(n)
            if change is not None:
                return change
        return None

    def _vwap_drawing(self, bar: Bar, vwap: float) -> list[DrawCommand]:
        """Úsečka VWAP od posledného bodu; bod je na konci baru, keď je hodnota známa."""
        end_ms = bar.time + self.step_ms
        prev = self._vwap_point
        self._vwap_point = (end_ms, vwap, self.vwap.day)
        if prev is None or prev[2] != self.vwap.day:
            return []
        return [DrawLine(VO_VWAP, prev[0], prev[1], end_ms, vwap, _VWAP_COLOR,
                         obj_id=f"vo_vwap.{end_ms}", text="VWAP")]
