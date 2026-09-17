"""Smer obchodov podľa indikátorov na vlastnom TF — rozšírenie portu, Pine ho nemá.

`tradeDirection` je v Pine oba smery / len long / len short. Port pridáva štvrtú voľbu
`Indicator`: zaškrtnuté indikátory (`indSupertrend`, `indAdx`) dajú stav — Supertrend
hore/dole, ADX/DMI hore/dole/do strany — a pravidlo pre tú kombináciu (`rule*`) povie,
či sa obchoduje oba smery, len long, len short, alebo vôbec. Kým sa niektorý zaškrtnutý
indikátor nerozbehne, neobchoduje sa.

ADX/DMI je TradingView „Directional Movement Index" (DI Length, ADX Smoothing) s prahom
`adxThreshold`: ADX pod ním = trh do strany, inak smer podľa väčšieho z +DI / −DI.

Supertrend je doslovný prepis TradingView skriptu „Supertrend" (Pine v4, KivancOzbilgic)
vrátane voľby `changeATR` (ATR = RMA, inak SMA z TR) a zdroja ceny. Pásmo sa posúva len
v smere trendu a trend sa otočí, keď close prerazí **predchádzajúce** pásmo.

Vyšší TF sa skladá z barov grafu rovnakým pravidlom ako `tradebot/core/candles.py`
(zarovnanie od epochy, perióda bez baru neexistuje), preto musí byť násobkom TF grafu.
HTF bar sa použije na bare grafu, ktorý ho **uzatvára** (close baru = koniec periódy) —
to je `request.security(..., lookahead_off)` na histórii v TradingView. Rozpracovaný HTF
bar sa nepoužije nikdy, takže filter nerepaintuje.

Predhistória je **vlastná**, nie v baroch grafu: Supertrend(10) potrebuje ~40 barov svojho
TF, ADX 14/14 ~111 (`warmup_bars`). Adaptér ich dá indikátoru pred prvým barom grafu
(`DirectionGate.add_warmup` → `tradebot.core.warmup.seed_engine`) z dát pred začiatkom behu,
takže `startup_candle_count` stratégie kvôli nim nerastie. Kým indikátor nemá svoje bary
(živý graf bez dostatočnej histórie, začiatok archívu), stav je „SA ROZBIEHA" a neobchoduje sa.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from tradebot.core.drawing import DrawBg, DrawBox, DrawCommand, DrawLabel, DrawLine, LabelStyle, with_alpha
from tradebot.core.types import Bar, Direction
from tradebot.core.warmup import Warmup, rma_bars, sma_bars

from ..config import (
    INDICATOR_RULES,
    IndicatorAction,
    PriceSource,
    TradeDirection,
    timeframe_option_minutes,
)
from ..drawing import ADX_STATE, ST_FILL, ST_LINE, ST_SIGNAL

if TYPE_CHECKING:
    from ..config import IBSConfig

__all__ = ["BoundaryAggregator", "Supertrend", "DMI", "DirectionGate"]

_UP_COLOR = "#16a34a"
_DOWN_COLOR = "#dc2626"
_SIDE_COLOR = "#94a3b8"


def price_of(bar: Bar, source: PriceSource) -> float:
    o, h, lo, c = bar.open, bar.high, bar.low, bar.close
    if source is PriceSource.OPEN:
        return o
    if source is PriceSource.HIGH:
        return h
    if source is PriceSource.LOW:
        return lo
    if source is PriceSource.CLOSE:
        return c
    if source is PriceSource.HLC3:
        return (h + lo + c) / 3.0
    if source is PriceSource.OHLC4:
        return (o + h + lo + c) / 4.0
    if source is PriceSource.HLCC4:
        return (h + lo + 2.0 * c) / 4.0
    return (h + lo) / 2.0


class BoundaryAggregator:
    """Bary vyššieho TF z barov grafu; HTF bar sa uzavrie na bare grafu, ktorý končí periódu.

    Keď posledný bar periódy chýba (víkend, výpadok dát), HTF bar sa uzavrie až prvým
    barom ďalšej periódy — skôr sa o jeho konci nedá vedieť.
    """

    __slots__ = ("ms", "step_ms", "_open_ts", "_o", "_h", "_l", "_c", "_v")

    def __init__(self, minutes: int, chart_tf_minutes: int) -> None:
        self.ms = int(minutes) * 60_000
        self.step_ms = int(chart_tf_minutes) * 60_000
        self._open_ts: int | None = None
        self._o = self._h = self._l = self._c = self._v = 0.0

    def _close(self) -> Bar:
        closed = Bar(time=self._open_ts, open=self._o, high=self._h, low=self._l,
                     close=self._c, volume=self._v)
        self._open_ts = None
        return closed

    def push(self, bar: Bar) -> list[Bar]:
        """Pridá bar grafu a vráti HTF bary, ktoré sa ním uzavreli (0, 1 alebo 2)."""
        closed: list[Bar] = []
        period = bar.time // self.ms * self.ms
        if self._open_ts is not None and period != self._open_ts:
            closed.append(self._close())
        if self._open_ts is None:
            self._open_ts = period
            self._o, self._h, self._l, self._c, self._v = bar.open, bar.high, bar.low, bar.close, bar.volume
        else:
            self._h = max(self._h, bar.high)
            self._l = min(self._l, bar.low)
            self._c = bar.close
            self._v += bar.volume
        if (bar.time + self.step_ms) % self.ms == 0:
            closed.append(self._close())
        return closed

    @property
    def started(self) -> bool:
        """Už je rozpracovaný HTF bar (dostal bar grafu alebo `prime`)."""
        return self._open_ts is not None

    def prime(self, partial: Bar | None) -> None:
        """Seeding: rozpracovaná perióda z barov pred behom (`tradebot.core.warmup.seed_engine`).

        `partial` je HTF bar poskladaný cez `tradebot.core.candles` z barov od začiatku
        periódy po prvý bar behu; ďalšie bary grafu ho doplnia, ako keby beh začal skôr.
        """
        if partial is None:
            return
        self._open_ts = partial.time // self.ms * self.ms
        self._o, self._h, self._l = partial.open, partial.high, partial.low
        self._c, self._v = partial.close, partial.volume


class Supertrend:
    """TradingView „Supertrend" (Pine v4) bar po bare.

    `trend` je +1/−1 (v Pine začína na 1), `ready` je `False`, kým ATR nemá dosť barov —
    vtedy Pine kreslí `na` a filter smer nepovoľuje.
    """

    __slots__ = ("period", "mult", "source", "change_atr", "_rma", "_tr_window",
                 "_prev_close", "up", "dn", "trend", "flipped", "ready", "bars")

    def __init__(self, period: int = 10, multiplier: float = 3.0,
                 source: PriceSource = PriceSource.HL2, change_atr: bool = True) -> None:
        self.period = max(1, int(period))
        self.mult = float(multiplier)
        self.source = PriceSource(source)
        self.change_atr = bool(change_atr)
        #: Pine `ta.rma` sa rozbieha z SMA prvých `period` hodnôt
        self._rma: float | None = None
        self._tr_window: deque[float] = deque(maxlen=self.period)
        self._prev_close: float | None = None
        self.up: float | None = None
        self.dn: float | None = None
        self.trend = 1
        self.flipped = False
        self.ready = False
        #: koľko barov vlastného TF prešlo výpočtom (aj zo seedingu)
        self.bars = 0

    @property
    def warmed(self) -> bool:
        """Prvá hodnota je (`ready`) a ATR sa ustálil (`warmup_bars` barov vlastného TF)."""
        return self.ready and self.bars >= self.warmup_bars

    @property
    def line(self) -> float | None:
        return self.up if self.trend == 1 else self.dn

    @property
    def warmup_bars(self) -> int:
        """Bary vlastného TF, kým sa ATR ustáli, + jeden bar pre pásmo z predchádzajúceho baru."""
        atr = rma_bars(self.period) if self.change_atr else sma_bars(self.period)
        return atr + 1

    def _atr(self, bar: Bar) -> float | None:
        prev = self._prev_close
        if prev is None:
            # Pine v4: `atr()` berie `tr(true)` = high-low, `sma(tr, n)` má na prvom bare na
            if self.change_atr:
                self._tr_window.append(bar.high - bar.low)
            return self._rma_step(None)
        tr = max(bar.high - bar.low, abs(bar.high - prev), abs(bar.low - prev))
        self._tr_window.append(tr)
        if self.change_atr:
            return self._rma_step(tr)
        return sum(self._tr_window) / self.period if len(self._tr_window) == self.period else None

    def _rma_step(self, tr: float | None) -> float | None:
        if self._rma is not None:
            self._rma += (tr - self._rma) / self.period
        elif len(self._tr_window) == self.period:
            self._rma = sum(self._tr_window) / self.period
        return self._rma

    def push(self, bar: Bar) -> int:
        self.bars += 1
        atr = self._atr(bar)
        prev_close, prev_up, prev_dn = self._prev_close, self.up, self.dn
        self._prev_close = bar.close
        self.flipped = False
        if atr is None:
            self.up = self.dn = None
            return self.trend
        src = price_of(bar, self.source)
        up = src - self.mult * atr
        up1 = prev_up if prev_up is not None else up
        if prev_close is not None and prev_close > up1:
            up = max(up, up1)
        dn = src + self.mult * atr
        dn1 = prev_dn if prev_dn is not None else dn
        if prev_close is not None and prev_close < dn1:
            dn = min(dn, dn1)
        before = self.trend
        if self.trend == -1 and bar.close > dn1:
            self.trend = 1
        elif self.trend == 1 and bar.close < up1:
            self.trend = -1
        self.flipped = self.ready and self.trend != before
        self.up, self.dn = up, dn
        self.ready = True
        return self.trend


class DMI:
    """TradingView „Directional Movement Index" (ADX a ±DI) bar po bare.

    Pine: `up = change(high)`, `down = -change(low)`, +DM/−DM len keď je pohyb väčší
    a kladný, `plus/minus = fixnan(100 * rma(DM, diLen) / rma(tr, diLen))`,
    `adx = 100 * rma(|plus − minus| / (plus + minus), adxSmoothing)`. Prvý bar nemá
    predchádzajúci, takže `tr` aj DM sú `na` a všetky RMA sa rozbiehajú od druhého baru.
    """

    __slots__ = ("di_len", "smoothing", "_prev", "_tr", "_plus_dm", "_minus_dm", "_dx",
                 "plus", "minus", "adx", "bars")

    def __init__(self, di_length: int = 14, adx_smoothing: int = 14) -> None:
        self.di_len = max(1, int(di_length))
        self.smoothing = max(1, int(adx_smoothing))
        self._prev: Bar | None = None
        self._tr = _RMA(self.di_len)
        self._plus_dm = _RMA(self.di_len)
        self._minus_dm = _RMA(self.di_len)
        self._dx = _RMA(self.smoothing)
        self.plus: float | None = None
        self.minus: float | None = None
        self.adx: float | None = None
        #: koľko barov vlastného TF prešlo výpočtom (aj zo seedingu)
        self.bars = 0

    @property
    def ready(self) -> bool:
        return self.adx is not None

    @property
    def warmed(self) -> bool:
        """ADX existuje a reťaz RMA sa ustálila (`warmup_bars` barov vlastného TF)."""
        return self.ready and self.bars >= self.warmup_bars

    @property
    def warmup_bars(self) -> int:
        """Reťaz RMA: prvý bar nemá predchádzajúci, potom ±DI (RMA `diLen`) a z nich ADX
        (RMA `adxSmoothing`) — ADX sa ustáli až po ustálení DI, preto súčet."""
        return 1 + rma_bars(self.di_len) + rma_bars(self.smoothing)

    def push(self, bar: Bar) -> float | None:
        self.bars += 1
        prev, self._prev = self._prev, bar
        if prev is None:
            return None
        up = bar.high - prev.high
        down = prev.low - bar.low
        tr = max(bar.high - bar.low, abs(bar.high - prev.close), abs(bar.low - prev.close))
        trur = self._tr.push(tr)
        plus_dm = self._plus_dm.push(up if up > down and up > 0 else 0.0)
        minus_dm = self._minus_dm.push(down if down > up and down > 0 else 0.0)
        if trur is None:
            return None
        if trur != 0:  # Pine: delenie nulou je `na` a `fixnan` podrží predošlú hodnotu
            self.plus = 100.0 * plus_dm / trur
            self.minus = 100.0 * minus_dm / trur
        if self.plus is None:
            return None
        total = self.plus + self.minus
        dx = self._dx.push(abs(self.plus - self.minus) / (total if total != 0 else 1.0))
        self.adx = None if dx is None else 100.0 * dx
        return self.adx

    def state(self, threshold: float) -> str | None:
        """`up` / `down` / `side` (ADX pod prahom alebo +DI = −DI), `None` kým sa nerozbehne."""
        if self.adx is None:
            return None
        if self.adx < threshold or self.plus == self.minus:
            return "side"
        return "up" if self.plus > self.minus else "down"


class _RMA:
    """Pine `ta.rma`: rozbeh z SMA prvých `n` hodnôt, potom Wilderova rekurzia."""

    __slots__ = ("n", "_seed", "value")

    def __init__(self, n: int) -> None:
        self.n = n
        self._seed: list[float] = []
        self.value: float | None = None

    def push(self, v: float) -> float | None:
        if self.value is not None:
            self.value += (v - self.value) / self.n
        else:
            self._seed.append(v)
            if len(self._seed) == self.n:
                self.value = sum(self._seed) / self.n
        return self.value


_STATE_TEXT = {"up": "HORE", "down": "DOLE", "side": "STRANA"}
_ACTION_TEXT = {
    IndicatorAction.BOTH: "OBA SMERY",
    IndicatorAction.LONG_ONLY: "LEN LONG",
    IndicatorAction.SHORT_ONLY: "LEN SHORT",
    IndicatorAction.NO_TRADE: "NEOBCHODOVAT",
}


class _Source:
    """Jeden zaškrtnutý indikátor na vlastnom TF: skladanie barov + výpočet + kresby."""

    def __init__(self, name: str, tf: str, chart_tf_minutes: int) -> None:
        minutes = timeframe_option_minutes(tf)
        if minutes < chart_tf_minutes or minutes % chart_tf_minutes:
            raise ValueError(
                f"{name}: TF {tf} ({minutes}m) nie je násobkom TF grafu {chart_tf_minutes}m — "
                "indikátor sa skladá z barov grafu, takže musí byť"
            )
        self.tf = tf
        self.minutes = minutes
        self.ratio = minutes // chart_tf_minutes
        self.agg = BoundaryAggregator(minutes, chart_tf_minutes)


class DirectionGate:
    """`tradeDirection = Indicator` pre stavový automat: aktualizuje sa každým barom grafu
    a povie, či smie zóna daného smeru položiť order.

    Každý zaškrtnutý indikátor má stav (Supertrend `up`/`down`, ADX aj `side`); dvojica
    stavov vyberie pravidlo z `INDICATOR_RULES` a jeho hodnota (`IndicatorAction`) povie,
    ktoré smery sú povolené. Kým sa niektorý indikátor nerozbehne, neobchoduje sa.
    """

    def __init__(self, cfg: "IBSConfig", chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.chart_tf_minutes = int(chart_tf_minutes)
        self.enabled = TradeDirection(cfg.tradeDirection) is TradeDirection.INDICATOR
        self.st: Supertrend | None = None
        self.dmi: DMI | None = None
        self._st_src: _Source | None = None
        self._dmi_src: _Source | None = None
        if not self.enabled:
            return
        if cfg.indSupertrend:
            self._st_src = _Source("Supertrend", cfg.stTimeframe, self.chart_tf_minutes)
            self.st = Supertrend(cfg.stAtrPeriod, cfg.stMultiplier, cfg.stSource, cfg.stChangeAtr)
        if cfg.indAdx:
            self._dmi_src = _Source("ADX/DMI", cfg.adxTimeframe, self.chart_tf_minutes)
            self.dmi = DMI(cfg.adxDiLength, cfg.adxSmoothing)

    def add_warmup(self, warmup: Warmup) -> Warmup:
        """Zaškrtnuté indikátory s **vlastnou** predhistóriou — `warmup_bars` barov ich TF.

        Predhistóriu grafu nezväčšujú: adaptér im tie bary dá pred prvým barom grafu cez
        `tradebot.core.warmup.seed_engine`. Bez seedingu (živý graf MultiCharts, začiatok
        dát) sa rozbehnú na grafe a kým nemajú svoje bary, brána hlási „SA ROZBIEHA".
        """
        if self.st is not None:
            warmup.add_seeded(f"Supertrend {self.st.period}", self.st.warmup_bars,
                              self._st_src.minutes, self._seed_st)
        if self.dmi is not None:
            warmup.add_seeded(f"ADX/DMI {self.dmi.di_len}/{self.dmi.smoothing}", self.dmi.warmup_bars,
                              self._dmi_src.minutes, self._seed_dmi)
        return warmup

    def _seed_st(self, bars, partial: Bar | None) -> None:
        self._seed(self.st, self._st_src, bars, partial)

    def _seed_dmi(self, bars, partial: Bar | None) -> None:
        self._seed(self.dmi, self._dmi_src, bars, partial)

    @staticmethod
    def _seed(indicator, src: _Source, bars, partial: Bar | None) -> None:
        """Uzavreté HTF bary pred behom výpočtom, rozpracovaná perióda do agregátora."""
        if indicator.bars or src.agg.started:
            raise RuntimeError(f"{src.tf}: seeding indikátora smie ísť len pred prvým barom grafu")
        for b in bars:
            indicator.push(b)
        src.agg.prime(partial)

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar) -> list[DrawCommand]:
        """Bar grafu; vráti kresby indikátorov, ktorých HTF bar sa ním uzavrel."""
        if not self.enabled:
            return []
        out: list[DrawCommand] = []
        if self.st is not None:
            for htf in self._st_src.agg.push(bar):
                self.st.push(htf)
                if self.st.ready:
                    out.extend(self._draw_st(htf))
        if self.dmi is not None:
            for htf in self._dmi_src.agg.push(bar):
                self.dmi.push(htf)
                if self.dmi.ready and self.cfg.adxShowState:
                    out.append(self._draw_dmi(htf))
        return out

    @property
    def states(self) -> tuple[str | None, str | None] | None:
        """(stav Supertrendu, stav ADX); `None` pre nezaškrtnutý; celé `None`, kým sa nerozbehnú."""
        st = dmi = None
        if self.st is not None:
            if not self.st.warmed:
                return None
            st = "up" if self.st.trend == 1 else "down"
        if self.dmi is not None:
            if not self.dmi.warmed:
                return None
            dmi = self.dmi.state(float(self.cfg.adxThreshold))
            if dmi is None:
                return None
        return st, dmi

    def action(self) -> IndicatorAction | None:
        states = self.states
        if states is None:
            return None
        return IndicatorAction(getattr(self.cfg, INDICATOR_RULES[states]))

    def allowed(self, direction: Direction) -> bool:
        if not self.enabled:
            return True
        action = self.action()
        return action is not None and action.allows(direction)

    def describe(self) -> str:
        """Stav do SKIP štítku, napr. `ST60 HORE + ADX60 STRANA`."""
        parts = []
        states = self.states or (None, None)
        if self.st is not None:
            parts.append(f"ST{self.cfg.stTimeframe} {_STATE_TEXT.get(states[0], 'SA ROZBIEHA')}")
        if self.dmi is not None:
            parts.append(f"ADX{self.cfg.adxTimeframe} {_STATE_TEXT.get(states[1], 'SA ROZBIEHA')}")
        return " + ".join(parts)

    def block_reason(self, direction: Direction) -> str | None:
        if self.allowed(direction):
            return None
        action = self.action()
        return f"{self.describe()}: {_ACTION_TEXT[action] if action else 'CAKA'}"

    # ------------------------------------------------------------------ #

    def _draw_st(self, htf: Bar) -> list[DrawCommand]:
        """Čiara platí od uzavretia HTF baru po uzavretie ďalšieho — tam ju brána používa."""
        st, ms = self.st, self._st_src.agg.ms
        up = st.trend == 1
        color = _UP_COLOR if up else _DOWN_COLOR
        start, end = htf.time + ms, htf.time + 2 * ms
        draws: list[DrawCommand] = [DrawLine(
            ST_LINE, start, st.line, end, st.line, color, width=2, obj_id=f"st.{htf.time}",
            text=f"Supertrend {self.cfg.stTimeframe} {'hore' if up else 'dole'}",
        )]
        if self.cfg.stHighlighting:
            # Pine `fill(ohlc4, čiara)`; box nemá šikmé hrany, tak ide po ohlc4 HTF baru
            mid = (htf.open + htf.high + htf.low + htf.close) / 4.0
            draws.append(DrawBox(
                ST_FILL, start, max(mid, st.line), end, min(mid, st.line), with_alpha(color, 100),
                fill_color=with_alpha(color, 85), border_width=0, obj_id=f"stf.{htf.time}",
            ))
        if st.flipped and self.cfg.stShowSignals:
            draws.append(DrawLabel(
                ST_SIGNAL, start, st.line, "Buy" if up else "Sell", "#ffffff",
                style=LabelStyle.UP if up else LabelStyle.DOWN, above=not up,
                bg_color=color, obj_id=f"sts.{htf.time}",
            ))
        return draws

    def _draw_dmi(self, htf: Bar) -> DrawCommand:
        dmi, ms = self.dmi, self._dmi_src.agg.ms
        state = dmi.state(float(self.cfg.adxThreshold))
        color = {"up": _UP_COLOR, "down": _DOWN_COLOR}.get(state, _SIDE_COLOR)
        return DrawBg(
            ADX_STATE, htf.time + ms, htf.time + 2 * ms, with_alpha(color, 90),
            obj_id=f"adx.{htf.time}",
            text=(f"ADX {self.cfg.adxTimeframe} {_STATE_TEXT[state].lower()}: ADX {dmi.adx:.1f}, "
                  f"+DI {dmi.plus:.1f}, −DI {dmi.minus:.1f}"),
        )
