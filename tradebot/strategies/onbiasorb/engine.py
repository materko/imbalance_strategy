"""Engine Overnight Bias ORB: smer dňa podľa polohy openu v overnight range, prerazenie 15m opening rangu.

Doslovný port Pine skriptu (`docs/sources/overnight_bias_orb.pine`). Časy CT:

  1. Overnight range: high/low od `onStartHHMM` do `rthHHMM` (štandardne polnoc – 8:30).
  2. Na prvom bare o `rthHHMM` alebo neskôr: poloha jeho openu v overnight range — horná tretina =
     len long, dolná = len short, stred = deň bez obchodu. Ten bar (8:30–8:45 na 15m grafe) je
     opening range.
  3. Signál od 8:45, keď sa bar zatvára v `minEntryHHMM` alebo neskôr a pred `exitHHMM`: zavretie nad
     high rangu (long) / pod low (short) v smere biasu a ADX > `adxMin`. Jeden obchod denne.
  4. Vstup market na otvorení ďalšej sviečky. SL = `slPct` % priemerného ATR (`avgatr`), TP = `rr` × SL,
     od zavretia signálnej sviečky (Pine od ceny vstupu).
  5. Časový exit na zavretí baru, ktorý sa zatvára v `exitHHMM` alebo neskôr (pred 16:00 CT).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup, decay_bars
from tradebot.strategies.ibs.ta.trend import DMI

from ..voltbreak.avgatr import SESSION_END_MIN, DailyAvgAtr, SessionAvgAtr
from .config import AtrSource, OnBiasOrbConfig, hhmm_minutes
from .drawing import OB_ENTRY, OB_OVERNIGHT, OB_RANGE, OB_THIRDS

__all__ = ["OnBiasOrbEngine"]

_CT = "America/Chicago"
_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_BOX_BARS = 8



def _seed_sessions(cfg) -> int:
    """Koľko seáns treba na ustálený priemer ATR: rozbeh RMA, kým váha štartu neklesne pod 0,01 % (SL je
    percento z ATR, takže aj malá odchýlka posunie stop o tick), + okno priemeru + rezerva."""
    n = max(1, int(cfg.atrLen))
    return n + decay_bars(1.0 / n, weight=0.0001) + int(cfg.avgLen) + 2

class OnBiasOrbEngine:
    def __init__(self, cfg: OnBiasOrbConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.zone = ZoneInfo(_CT)
        self.on_s = hhmm_minutes(cfg.onStartHHMM)
        self.rth = hhmm_minutes(cfg.rthHHMM)
        self.ex = hhmm_minutes(cfg.exitHHMM)
        self.min_entry = hhmm_minutes(cfg.minEntryHHMM)
        self.sess_atr = SessionAvgAtr(cfg.atrLen, cfg.avgLen)
        self.daily_atr = DailyAvgAtr(cfg.atrLen, cfg.avgLen)
        self.dmi = DMI(int(cfg.adxLen), int(cfg.adxLen))
        self.warmup = Warmup(self.chart_tf_minutes).add(f"ADX {cfg.adxLen}", self.dmi.warmup_bars)
        # Priemer ATR za N seáns (a ADX) dostane predhistóriu z dát pred behom: prehrajú sa nimi bary grafu
        # bez obchodov. Bez toho by štart v inom dni dával iné obchody, kým sa priemer nerozbehne (krok 1 smernice).
        self.warmup.add_seeded(f"ATR {cfg.atrLen} za {cfg.avgLen} seáns", _seed_sessions(cfg) * 1380 // self.chart_tf_minutes,
                               self.chart_tf_minutes, self._seed)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=8, atr_len=14)

        self._prev_min: int | None = None
        self._prev_day = None
        self._prev_in_on = False
        self.on_h: float | None = None
        self.on_l: float | None = None
        self._on_start_ms: int | None = None
        self.or_h: float | None = None
        self.or_l: float | None = None
        self.bias = 0
        self.traded_today = False

    @property
    def avg_atr(self) -> float | None:
        return self.daily_atr.value if self.cfg.atrSource is AtrSource.DAILY else self.sess_atr.value

    def _in_overnight(self, m: int) -> bool:
        if self.on_s < self.rth:
            return self.on_s <= m < self.rth
        return m >= self.on_s or m < self.rth

    def _seed(self, bars, partial) -> None:
        for b in bars:
            self.on_bar(b, ctx=MarketContext(in_trade_window=True))

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index

        local = datetime.fromtimestamp(bar.time / 1000, tz=self.zone)
        close_local = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=self.zone)
        bar_min = local.hour * 60 + local.minute
        close_min = close_local.hour * 60 + close_local.minute
        day = local.date()
        new_day = self._prev_day is None or day != self._prev_day

        self.sess_atr.push(bar, bar_min)
        self.daily_atr.push(bar, local)
        adx = self.dmi.push(bar)

        in_on = self._in_overnight(bar_min)
        rth_start = bar_min >= self.rth and (new_day or (self._prev_min is not None and self._prev_min < self.rth))
        if in_on and not self._prev_in_on:
            self.on_h, self.on_l, self._on_start_ms = bar.high, bar.low, bar.time
        elif in_on and self.on_h is not None:
            self.on_h = max(self.on_h, bar.high)
            self.on_l = min(self.on_l, bar.low)

        if rth_start:
            rng = (self.on_h - self.on_l) if self.on_h is not None else None
            pos = (bar.open - self.on_l) / rng if rng and rng > 0 else 0.5
            self.bias = 1 if pos > 2.0 / 3.0 else -1 if pos < 1.0 / 3.0 else 0
            self.or_h, self.or_l = bar.high, bar.low
            self.traded_today = False
            out.drawings += self._draw_day(bar)

        after_or = bar_min >= self.rth + 15 and close_min >= self.min_entry and close_min < self.ex
        flat = ctx.position_size == 0.0
        adx_ok = adx is not None and adx > cfg.adxMin
        direction = None
        if after_or and flat and not self.traded_today and adx_ok and self.or_h is not None:
            if self.bias == 1 and bar.close > self.or_h:
                direction = Direction.LONG
            elif self.bias == -1 and bar.close < self.or_l:
                direction = Direction.SHORT
        if direction is not None:
            plan = self._plan(bar, direction)
            if plan is not None:
                self.traded_today = True
                long = direction is Direction.LONG
                out.orders.append(OrderIntent(OrderAction.ENTRY, f"ob:{idx}", idx, direction=direction, plan=plan,
                                              order_type=OrderType.MARKET,
                                              reason=f"prerazenie opening rangu v smere biasu ({'long' if long else 'short'})"))
                out.drawings.append(DrawLabel(OB_ENTRY, bar.time, bar.low if long else bar.high,
                                              "LONG" if long else "SHORT", "#ffffff",
                                              style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                              bg_color=_LONG_COLOR if long else _SHORT_COLOR,
                                              obj_id=f"ob_entry.{bar.time}"))
                out.drawings += self._trade_boxes(bar, plan)

        if cfg.useTimeExit and not flat and close_min >= self.ex and bar_min < SESSION_END_MIN:
            out.close_session = True
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason="časový exit"))

        self._prev_min, self._prev_day, self._prev_in_on = bar_min, day, in_on
        return out

    def _plan(self, bar: Bar, direction: Direction) -> TradePlan | None:
        cfg = self.cfg
        avg = self.avg_atr
        if avg is None:                      # Pine by vstúpil bez stopu; bez ATR sa tu neobchoduje
            return None
        sl_distance = cfg.slPct / 100.0 * avg
        if sl_distance < self.inst.tick_size * 2:
            return None
        long = direction is Direction.LONG
        entry = bar.close
        stop = entry - sl_distance if long else entry + sl_distance
        take = entry + sl_distance * cfg.rr if long else entry - sl_distance * cfg.rr
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl_distance) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl_distance)

    def _draw_day(self, bar: Bar) -> list[DrawCommand]:
        if not self.cfg.showLevels:
            return []
        cmds: list[DrawCommand] = []
        right = bar.time + (self.ex - self.rth) * 60_000
        if self.on_h is not None and self._on_start_ms is not None:
            color = "#14b8a6"
            cmds.append(DrawBox(kind=OB_OVERNIGHT, x1_ms=self._on_start_ms, y1=self.on_h, x2_ms=bar.time,
                                y2=self.on_l, border_color=color, fill_color=color + "14", border_width=1,
                                obj_id=f"ob_on.{bar.time}"))
            for k, frac in (("top", 2.0 / 3.0), ("bot", 1.0 / 3.0)):
                y = self.on_l + (self.on_h - self.on_l) * frac
                cmds.append(DrawLine(OB_THIRDS, self._on_start_ms, y, right, y, "#9ca3af",
                                     obj_id=f"ob_{k}.{bar.time}"))
        bias_color = _LONG_COLOR if self.bias == 1 else _SHORT_COLOR if self.bias == -1 else "#9ca3af"
        cmds.append(DrawBox(kind=OB_RANGE, x1_ms=bar.time, y1=bar.high, x2_ms=right, y2=bar.low,
                            border_color="#f59e0b", fill_color=bias_color + "18", border_width=1,
                            obj_id=f"ob_or.{bar.time}",
                            text={1: "bias LONG", -1: "bias SHORT"}.get(self.bias, "bez biasu")))
        return cmds

    def _trade_boxes(self, bar: Bar, plan: TradePlan) -> list[DrawCommand]:
        right = bar.time + _BOX_BARS * self.step_ms
        return [
            DrawBox(kind=kind, x1_ms=bar.time, y1=max(plan.entry, price), x2_ms=right,
                    y2=min(plan.entry, price), border_color=color, fill_color=color + "40",
                    border_width=0, obj_id=f"ob{bar.time}.{kind.value}")
            for kind, price, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR),
                                       (DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR))
        ]

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
