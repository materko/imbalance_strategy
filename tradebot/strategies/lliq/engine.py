"""Engine LONDON LIQUIDITY IFVG 1.0 — prepis Rust stratégie `LondonSweepIfvg` (`rq_sdk`, Shujat) bar po bare.

Čas = otvorenie baru v New Yorku (HHMM). Na každom uzavretom bare v poradí predlohy:

  1. **poistky seansy** — seansa otvorená viac ako 24 h (a pred stavovým automatom viac ako 20 h) sa zruší,
  2. **nový deň** (dátum NY) — vynulovať sweep, IFVG a otvorenú seansu,
  3. **seansa** `sessionStart`–`sessionEnd`: začiatok, rozšírenie high / low, koniec → úrovne high / low a čiary,
  4. **sweep (LS)** — v okne `lsStart`–`lsEnd`, po konci seansy, ešte bez LS: zavretie nad high úrovne a neskôr
     zavretie späť pod ňu veľkým telom (> 50 % sviečky) = LS short (cena = high baru); zrkadlovo pre low,
  5. **FVG** — trojsviečkové medzery (high pred dvoma barmi < low teraz = býčie) vznikajúce v seanse alebo po LS
     toho dňa (najviac 64),
  6. **inverzia** — FVG staršie ako `maxIfvgAgeHours`, z iného dňa alebo po vstupe dňa sa zahodí; zavretie pod
     dolný okraj býčieho (nad horný medvedieho) po LS mimo seansy v okne LS, v smere LS a na správnej strane ceny LS
     = vstup; stop swing (`swingLookback` barov) alebo ATR, cieľ úroveň seansy / RR / ATR,
  7. **filter dní** a vstup trhom (jeden za deň — po inverzii sa ďalšie FVG dňa zahodia).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawLabel, DrawLine, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ..rqport import TradeDraw, market_entry
from .config import LliqConfig
from .drawing import LLIQ_ENTRY, LLIQ_MARK, LLIQ_SESSION

__all__ = ["LliqEngine"]

NY = ZoneInfo("America/New_York")
_H = 3_600_000
_MAX_FVG = 64
_GREY = "#808080"


@dataclass
class _Fvg:
    start_ms: int
    lower: float
    upper: float
    bull: bool
    day: object


def _in_window(hhmm: int, start: int, end: int) -> bool:
    return start <= hhmm < end if start <= end else hhmm >= start or hhmm < end


class LliqEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: LliqConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        n = max(int(cfg.swingLookback), 3)
        self.history = BarHistory(maxlen=n + 1, atr_len=max(1, int(cfg.atrLength)))
        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrLength}", self.history.atr_warmup_bars)
        self.required_history = max(1, self.warmup.chart_bars)
        self.bars: list[Bar] = []
        self.last_day = None
        self.s_active = False
        self.s_high = float("-inf")
        self.s_low = float("inf")
        self.s_start = -1
        self.high_level = float("nan")
        self.low_level = float("nan")
        self.lines_active = False
        self.high_swept = self.low_swept = False
        self.ls = False
        self.ls_ms = -1
        self.ls_day = None
        self.ls_dir = 0
        self.ls_price = float("nan")
        self.done = False
        self.fvgs: list[_Fvg] = []
        self.draw = TradeDraw(self.step_ms)

    def _reset_ls(self) -> None:
        self.ls, self.ls_ms, self.ls_day, self.ls_dir = False, -1, None, 0
        self.ls_price = float("nan")
        self.done = False

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        self.bars.append(bar)
        if len(self.bars) > max(int(cfg.swingLookback), 3):
            self.bars.pop(0)
        t = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        hhmm, today = t.hour * 100 + t.minute, t.date()
        self.draw.tick(out, bar, pos)
        s0, s1 = int(cfg.sessionStart), int(cfg.sessionEnd)

        # ---- 1. poistka 24 h ------------------------------------------------------- #
        if self.s_active and self.s_start >= 0 and bar.time - self.s_start > 24 * _H:
            self.s_active, self.s_high, self.s_low = False, float("-inf"), float("inf")
        # ---- 2. nový deň ------------------------------------------------------------- #
        if self.last_day is not None and today != self.last_day:
            self.s_active, self.s_high, self.s_low = False, float("-inf"), float("inf")
            self.high_swept = self.low_swept = False
            self.lines_active = False
            self._reset_ls()
        self.last_day = today
        in_session = _in_window(hhmm, s0, s1)
        if self.s_active and bar.time - self.s_start > 20 * _H:
            self.s_active, self.s_high, self.s_low = False, float("-inf"), float("inf")

        # ---- 3. seansa --------------------------------------------------------------- #
        if in_session and not self.s_active:
            self.s_active, self.s_high, self.s_low, self.s_start = True, bar.high, bar.low, bar.time
            self.lines_active = False
            self._reset_ls()
        elif in_session and self.s_active:
            self.s_high, self.s_low = max(self.s_high, bar.high), min(self.s_low, bar.low)
        elif not in_session and self.s_active:
            self.high_level, self.low_level = self.s_high, self.s_low
            self.s_active = False
            self.lines_active = True
            out.drawings.append(DrawBox(LLIQ_SESSION, self.s_start, self.s_high, bar.time, self.s_low, _GREY,
                                        fill_color=with_alpha(_GREY, 40), obj_id=f"lliq.s.{self.s_start}", text="SEANSA"))
            for lvl, col, nm in ((self.high_level, "#ff0000", "h"), (self.low_level, "#008000", "l")):
                out.drawings.append(DrawLine(LLIQ_SESSION, bar.time, lvl, bar.time + 6 * self.step_ms, lvl, col,
                                             width=1, obj_id=f"lliq.{nm}.{bar.time}"))

        # ---- 4. sweep (LS) --------------------------------------------------------------- #
        ls_ok = _in_window(hhmm, int(cfg.lsStart), int(cfg.lsEnd))
        rng = bar.high - bar.low
        big = rng > 0 and abs(bar.open - bar.close) * 100.0 / rng > 50.0
        if self.high_level == self.high_level and self.lines_active and not self.ls and ls_ok:
            if bar.close > self.high_level:
                self.high_swept = True
            if self.high_swept and bar.close <= self.high_level and big:
                self.ls, self.ls_ms, self.ls_day, self.ls_dir, self.ls_price = True, bar.time, today, -1, bar.high
                self.high_swept = False
                out.drawings.append(DrawLabel(LLIQ_MARK, bar.time, bar.high, "LS", "#ffffff", style=LabelStyle.DOWN,
                                              above=True, bg_color="#ff0000", obj_id=f"lliq.ls.{bar.time}"))
        if self.low_level == self.low_level and self.lines_active and not self.ls and ls_ok:
            if bar.close < self.low_level:
                self.low_swept = True
            if self.low_swept and bar.close >= self.low_level and big:
                self.ls, self.ls_ms, self.ls_day, self.ls_dir, self.ls_price = True, bar.time, today, 1, bar.low
                self.low_swept = False
                out.drawings.append(DrawLabel(LLIQ_MARK, bar.time, bar.low, "LS", "#ffffff", style=LabelStyle.UP,
                                              above=False, bg_color="#008000", obj_id=f"lliq.ls.{bar.time}"))

        # ---- 5. FVG ------------------------------------------------------------------------ #
        if idx >= 2 and len(self.bars) >= 3:
            b2 = self.bars[-3]
            track = (in_session and not self.done) or (self.ls and not self.done and self.ls_day == today
                                                       and self.ls_ms >= 0 and bar.time > self.ls_ms)
            if track and b2.high < bar.low and len(self.fvgs) < _MAX_FVG:
                self.fvgs.append(_Fvg(b2.time, b2.high, bar.low, True, today))
            if track and b2.low > bar.high and len(self.fvgs) < _MAX_FVG:
                self.fvgs.append(_Fvg(b2.time, bar.high, b2.low, False, today))

        # ---- 6. inverzia ------------------------------------------------------------------- #
        signal = None
        if self.fvgs:
            atr = self.history.atr
            if atr <= 0:
                return out
            for i in range(len(self.fvgs) - 1, -1, -1):
                f = self.fvgs[i]
                if bar.time - f.start_ms > int(cfg.maxIfvgAgeHours) * _H or f.day != today or self.done:
                    self.fvgs.pop(i)
                    continue
                inverted = bar.close < f.lower if f.bull else bar.close > f.upper
                bear = f.bull
                dir_ok = (self.ls_dir == -1 and bear) or (self.ls_dir == 1 and not bear)
                nan = self.ls_price != self.ls_price
                side_ok = (nan or f.lower <= self.ls_price) if bear else (nan or f.upper >= self.ls_price)
                if inverted and self.ls and not in_session and ls_ok and dir_ok and side_ok:
                    n = max(1, int(cfg.swingLookback))
                    sw = self.bars[-n:]
                    if bear:
                        sl = bar.close + atr * cfg.slAtrMult if int(cfg.slType) == 1 else max(b.high for b in sw)
                        risk = sl - bar.close
                        tp = {1: bar.close - risk * cfg.riskReward, 2: bar.close - atr * cfg.tpAtrMult}.get(
                            int(cfg.tpType), self.low_level)
                    else:
                        sl = bar.close - atr * cfg.slAtrMult if int(cfg.slType) == 1 else min(b.low for b in sw)
                        risk = bar.close - sl
                        tp = {1: bar.close + risk * cfg.riskReward, 2: bar.close + atr * cfg.tpAtrMult}.get(
                            int(cfg.tpType), self.high_level)
                    signal = (not bear, sl, tp)
                    out.drawings.append(DrawBox(LLIQ_MARK, max(f.start_ms, bar.time - 23 * _H), f.upper, bar.time,
                                                f.lower, "#ff0000" if bear else "#008000",
                                                fill_color=with_alpha("#ff0000" if bear else "#008000", 50),
                                                obj_id=f"lliq.f.{f.start_ms}.{bar.time}", text="IFVG"))
                    self.done = True
                    self.fvgs.pop(i)

        # ---- 7. filter dní a vstup ------------------------------------------------------------ #
        if signal is None or pos != 0.0:
            return out
        if cfg.useDayFilter and not {1: cfg.tradeMon, 2: cfg.tradeTue, 3: cfg.tradeWed, 4: cfg.tradeThu,
                                     5: cfg.tradeFri}.get(t.isoweekday(), False):
            return out
        long, sl, tp = signal
        if tp != tp or sl != sl:
            return out
        plan = market_entry(out, cfg, self.inst, bar, idx, "lliq", long, sl, tp,
                            f"London IFVG {'long' if long else 'short'} po LS")
        if plan:
            self.draw.start(out, bar, "lliq", plan.entry, plan.stop_loss, plan.take_profit, LLIQ_ENTRY,
                            "IFVG long" if long else "IFVG short", long)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
