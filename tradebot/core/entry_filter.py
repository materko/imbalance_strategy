"""Filter trendu a volatility — spoločný filter vstupov pre stratégie, ktoré ho nemajú vlastný.

Stratégia (engine) rozhodne, **kedy** vstúpiť; keď má config `trendFilter` iné než `off`, obal
`EntryFilterEngine` vstup pustí len v zadanom vzťahu k trendu:

* ``with``    — long len keď je zavretie nad EMA, short len pod ňou (s trendom),
* ``against`` — naopak (proti trendu, návrat k priemeru).

Filter volatility (`volFilter`): ATR(14) grafu sa porovná s jeho priemerom za `volLookback` barov —
``low`` pustí vstup len v pokojnom trhu (ATR pod priemerom), ``high`` len v rozkývanom (nad priemerom).

Filter špičky volatility (`spikeFilter`, 24. 11. 2026): špička = Ø denný rozsah posledných `spikeShortDays`
uzavretých dní / Ø za `spikeLongDays` dní; deň = obchodný deň CME (18:00 → 17:00 New York), rozsah =
(high − low) / posledné zavretie dňa v %, deň s menej než `_SPIKE_MIN_MINUTES` minútami barov (sviatok) sa nepočíta.
Číslo sa určí na prvom bare dňa a cez deň sa nemení; pri špičke nad `spikeMax` sa v ten deň nový vstup nepustí
(otvorená pozícia beží ďalej). Kým nie je `spikeLongDays` dní, vstupy púšťa. Pole majú aj stratégie s vlastným
filtrom trendu (IBS a odnože: `SpikeFilterFields`) — obal sa vtedy nasadí len kvôli špičke.

EMA má dĺžku `trendEmaLen` a počíta sa zo zavretí na `trendTF` minútach (0 = TF grafu); vyšší TF sa
skladá z barov grafu a do EMA ide až uzavretý bar. Predhistóriu dostane seedom pred prvým barom
(`Warmup.add_seeded`); kým nemá `trendEmaLen` barov, vstupy nepúšťa.

Obal je generický (nepozná stratégiu menom), platí pre market aj limit vstupy a nasadzujú ho adaptéry
ako najvnútornejší (pod potvrdenie sviečkou a typ orderu). Pri `off` sa engine nebalí. IBS a odnože
a Liquidity majú vlastné filtre trendu.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from .engine import EngineOutput
from .orders import MarketContext, OrderAction
from .types import Bar, Direction
from .warmup import ema_bars
from .entry_draw import trade_drawings, with_ids

__all__ = ["TrendFilter", "VolFilter", "EntryFilterFields", "ENTRY_FILTER_ENUMS", "ENTRY_FILTER_CONSTRAINTS",
           "ENTRY_FILTER_FIELD_NAMES", "entry_filter_params", "EntryFilterEngine", "wrap_entry_filter",
           "SpikeFilterFields", "SPIKE_FIELD_NAMES", "SPIKE_CONSTRAINTS", "spike_filter_params"]


class TrendFilter(str, Enum):
    OFF = "off"
    WITH = "with"        # len v smere trendu
    AGAINST = "against"  # len proti trendu


class VolFilter(str, Enum):
    OFF = "off"
    LOW = "low"    # len pokojný trh: ATR pod svojím priemerom
    HIGH = "high"  # len rozkývaný trh: ATR nad svojím priemerom


_ATR_LEN = 14
_NY = ZoneInfo("America/New_York")
#: deň CME s menej minútami barov sa do špičky nepočíta (sviatky, skrátené dni)
_SPIKE_MIN_MINUTES = 300


@dataclass
class SpikeFilterFields:
    """Mixin polí filtra špičky volatility — aj pre stratégie s vlastným filtrom trendu (IBS)."""

    spikeFilter: bool = False
    spikeShortDays: int = 5
    spikeLongDays: int = 60
    spikeMax: float = 1.7


SPIKE_FIELD_NAMES: frozenset[str] = frozenset({"spikeFilter", "spikeShortDays", "spikeLongDays", "spikeMax"})
SPIKE_CONSTRAINTS: dict[str, tuple[float, float]] = {"spikeShortDays": (1, 60), "spikeLongDays": (2, 500),
                                                      "spikeMax": (0.5, 10.0)}


def spike_filter_params(group: str) -> dict[str, dict[str, Any]]:
    """Popisy polí filtra špičky pre formulár webapp."""
    return {
        "spikeFilter": dict(group=group, title="Filter špičky volatility",
                            tooltip="Neotvárať obchod v deň, keď je Ø denný rozsah posledných dní nad spikeMax × bežný."),
        "spikeShortDays": dict(group=group, title="Špička: posledné dni", inline="spike", tooltip="Krátky priemer denného rozsahu."),
        "spikeLongDays": dict(group=group, title="Špička: bežný za (dni)", inline="spike", tooltip="Dlhý priemer = bežný stav."),
        "spikeMax": dict(group=group, title="Špička: najviac (×)", step=0.05,
                         tooltip="1,0 = bežný trh; 1,7 = posledné dni o 70 % divokejšie než bežne → v ten deň bez nového obchodu."),
    }


@dataclass
class EntryFilterFields(SpikeFilterFields):
    """Mixin polí configu. Pridáva sa ako ďalší predok configu stratégie."""

    trendFilter: TrendFilter = TrendFilter.OFF
    trendEmaLen: int = 200
    trendTF: int = 0
    volFilter: VolFilter = VolFilter.OFF
    volLookback: int = 100


ENTRY_FILTER_FIELD_NAMES: frozenset[str] = frozenset({"trendFilter", "trendEmaLen", "trendTF", "volFilter",
                                                      "volLookback"}) | SPIKE_FIELD_NAMES
ENTRY_FILTER_ENUMS: dict[str, type] = {"trendFilter": TrendFilter, "volFilter": VolFilter}
ENTRY_FILTER_CONSTRAINTS: dict[str, tuple[float, float]] = {**SPIKE_CONSTRAINTS, "trendEmaLen": (2, 1000), "trendTF": (0, 1440),
                                                            "volLookback": (10, 2000)}


def entry_filter_params(group: str) -> dict[str, dict[str, Any]]:
    """Popisy polí pre formulár webapp (do `params.py` stratégie)."""
    return {
        "trendFilter": dict(group=group, title="Filter trendu (EMA)",
                            tooltip="off = bez filtra; with = long len nad EMA a short len pod nou; against = naopak."),
        "trendEmaLen": dict(group=group, title="Filter trendu: dlzka EMA", tooltip="Klasika 50 / 100 / 200."),
        "trendTF": dict(group=group, title="Filter trendu: TF (min)",
                        tooltip="Na akom TF sa EMA pocita. 0 = TF grafu; 60 = hodinova, 240 = stvorhodinova."),
        "volFilter": dict(group=group, title="Filter volatility",
                          tooltip="off = bez filtra; low = len pokojny trh (ATR(14) pod svojim priemerom); high = len rozkyvany."),
        "volLookback": dict(group=group, title="Filter volatility: priemer za (bary)", tooltip="Z kolkych barov grafu sa ATR priemeruje."),
        **spike_filter_params(group),
    }


class EntryFilterEngine:
    """Obal enginu: vstupy stratégie púšťa len v zadanom vzťahu k EMA (viď hlavičku modulu)."""

    def __init__(self, engine: Any, cfg: Any, chart_tf_minutes: int) -> None:
        self.engine = engine
        self.cfg = cfg
        common = hasattr(cfg, "trendTF")       # IBS a odnože majú len filter špičky
        self.mode = TrendFilter(getattr(cfg, "trendFilter", TrendFilter.OFF)) if common else TrendFilter.OFF
        self.vol_mode = VolFilter(getattr(cfg, "volFilter", VolFilter.OFF)) if common else VolFilter.OFF
        self.vol_n = int(getattr(cfg, "volLookback", 100))
        self.atr = 0.0
        self._tr: list[float] = []
        self._prev_close: float | None = None
        self._atrs: deque[float] = deque(maxlen=self.vol_n)
        self._atr_sum = 0.0
        self.n = int(getattr(cfg, "trendEmaLen", 200))
        chart = max(1, int(chart_tf_minutes))
        tf = int(getattr(cfg, "trendTF", 0)) or chart
        if tf < chart or tf % chart:
            tf = -(-max(tf, chart) // chart) * chart
        self.tf = tf
        self._tf_ms = tf * 60_000
        self._chart_ms = chart * 60_000
        self.ema: float | None = None
        self._count = 0
        self._sum = 0.0
        self._bucket: int | None = None
        self._last_close: float | None = None
        self._dropped: set[str] = set()
        self.spike_on = bool(getattr(cfg, "spikeFilter", False))
        self.spike_s = int(getattr(cfg, "spikeShortDays", 5))
        self.spike_l = int(getattr(cfg, "spikeLongDays", 60))
        self.spike_max = float(getattr(cfg, "spikeMax", 1.7))
        self.spike: float | None = None       # špička dnešného dňa (z uzavretých dní)
        self._ranges: deque[float] = deque(maxlen=self.spike_l)
        self._chart_min = chart
        self._day = None
        self._dh = self._dl = self._dc = 0.0
        self._dmin = 0
        warmup = getattr(engine, "warmup", None)
        if warmup is not None and hasattr(warmup, "add_seeded"):
            if self.mode is not TrendFilter.OFF:
                warmup.add_seeded(f"filter trendu EMA {self.n} na {tf}m", ema_bars(self.n), tf, self._seed)
            if self.vol_mode is not VolFilter.OFF:
                warmup.add_seeded(f"filter volatility ATR {_ATR_LEN} / {self.vol_n} barov", self.vol_n + 4 * _ATR_LEN,
                                  chart, self._seed_vol)
            if self.spike_on:
                # spikeLongDays obchodných dní ≈ 1,5 × toľko kalendárnych (víkendy, sviatky) + rezerva
                warmup.add_seeded(f"filter špičky volatility {self.spike_s} / {self.spike_l} dní",
                                  (self.spike_l * 3 // 2 + 5) * 1440 // chart, chart, self._seed_spike)

    def __getattr__(self, name: str) -> Any:   # inst, required_history, warmup, final_drawings…
        if name == "engine" or name.startswith("__"):
            raise AttributeError(name)   # pri unpickle ešte `engine` nie je — bez tohto nekonečná rekurzia
        return getattr(self.engine, name)

    # ---- EMA -------------------------------------------------------------- #

    def _close(self, close: float) -> None:
        """Uzavretý bar TF filtra. Štart ako Pine `ta.ema`: priemer prvých `n` zavretí."""
        self._count += 1
        if self.ema is None:
            self._sum += close
            if self._count >= self.n:
                self.ema = self._sum / self.n
        else:
            self.ema += (close - self.ema) * 2.0 / (self.n + 1)

    def _seed(self, bars, partial: Bar | None) -> None:
        for b in bars:
            self._close(b.close)
        if partial is not None:
            self._bucket = partial.time // self._tf_ms
            self._last_close = partial.close

    def _vol(self, bar: Bar) -> None:
        pc = self._prev_close
        tr = bar.high - bar.low if pc is None else max(bar.high - bar.low, abs(bar.high - pc), abs(bar.low - pc))
        self._prev_close = bar.close
        if self.atr > 0:
            self.atr += (tr - self.atr) / _ATR_LEN
        else:
            self._tr.append(tr)
            if len(self._tr) < _ATR_LEN:
                return
            self.atr = sum(self._tr) / len(self._tr)
        if len(self._atrs) == self._atrs.maxlen:
            self._atr_sum -= self._atrs[0]
        self._atrs.append(self.atr)
        self._atr_sum += self.atr

    def _seed_vol(self, bars, partial: Bar | None) -> None:
        for b in bars:
            self._vol(b)

    # ---- špička volatility --------------------------------------------- #

    def _spike_push(self, bar: Bar) -> None:
        day = (datetime.fromtimestamp(bar.time / 1000, tz=_NY) + timedelta(hours=6)).date()   # deň CME od 18:00
        if day != self._day:
            if self._day is not None and self._dmin >= _SPIKE_MIN_MINUTES and self._dc > 0:
                self._ranges.append((self._dh - self._dl) / self._dc * 100.0)
                if len(self._ranges) >= self.spike_l:
                    short = list(self._ranges)[-self.spike_s:]
                    self.spike = (sum(short) / len(short)) / (sum(self._ranges) / len(self._ranges))
            self._day, self._dh, self._dl, self._dmin = day, bar.high, bar.low, 0
        else:
            self._dh = max(self._dh, bar.high)
            self._dl = min(self._dl, bar.low)
        self._dc = bar.close
        self._dmin += self._chart_min

    def _seed_spike(self, bars, partial: Bar | None) -> None:
        for b in bars:
            self._spike_push(b)

    def spike_allows(self) -> bool:
        return not self.spike_on or self.spike is None or self.spike <= self.spike_max

    def vol_allows(self) -> bool:
        if self.vol_mode is VolFilter.OFF:
            return True
        if len(self._atrs) < self.vol_n:
            return False
        mean = self._atr_sum / len(self._atrs)
        return self.atr < mean if self.vol_mode is VolFilter.LOW else self.atr > mean

    def _push(self, bar: Bar) -> None:
        bucket = bar.time // self._tf_ms
        if self._bucket is not None and bucket != self._bucket and self._last_close is not None:
            self._close(self._last_close)       # perióda sa skončila bez toho, aby sme videli jej posledný bar
            self._last_close = None
        self._bucket = bucket
        self._last_close = bar.close
        if (bar.time + self._chart_ms) // self._tf_ms != bucket:    # posledný bar grafu v perióde — bar TF je uzavretý
            self._close(bar.close)
            self._last_close = None

    def allows(self, direction: Direction, close: float) -> bool:
        if not self.spike_allows():
            return False
        if not self.vol_allows():
            return False
        if self.mode is TrendFilter.OFF:
            return True
        if self.ema is None:
            return False
        above = close > self.ema
        long = direction is Direction.LONG
        return (above == long) if self.mode is TrendFilter.WITH else (above != long)

    def on_bar(self, bar: Bar, htf: Any = None, ctx: MarketContext | None = None) -> EngineOutput:
        if self.mode is not TrendFilter.OFF:
            self._push(bar)
        if self.vol_mode is not VolFilter.OFF:
            self._vol(bar)
        if self.spike_on:
            self._spike_push(bar)
        out = self.engine.on_bar(bar, htf, with_ids(ctx, set(), self._dropped))
        self._dropped = set()
        kept = []
        for o in out.orders:
            if o.action is OrderAction.ENTRY and o.plan is not None and not self.allows(o.plan.direction, bar.close):
                objs = trade_drawings(out.drawings, bar.time)    # zahodený vstup — jeho kresba tiež
                out.drawings = [d for d in out.drawings if not any(d is x for x in objs)]
                self._dropped.add(o.order_id)
                continue
            kept.append(o)
        out.orders = kept
        return out


def wrap_entry_filter(engine: Any, cfg: Any, chart_tf_minutes: int) -> Any:
    """Engine obalený filtrom trendu, keď to config chce; inak ten istý engine."""
    if getattr(engine, "native_entry_layers", False):   # C# engine má obaly vstupov v sebe
        return engine
    if getattr(cfg, "spikeFilter", False):
        return EntryFilterEngine(engine, cfg, chart_tf_minutes)
    t = getattr(cfg, "trendFilter", None)
    if t is None or not hasattr(cfg, "trendTF"):
        return engine
    if TrendFilter(t) is TrendFilter.OFF and VolFilter(getattr(cfg, "volFilter", VolFilter.OFF)) is VolFilter.OFF:
        return engine
    return EntryFilterEngine(engine, cfg, chart_tf_minutes)
