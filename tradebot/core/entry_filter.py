"""Filter trendu — spoločný filter vstupov pre stratégie, ktoré ho nemajú vlastný.

Stratégia (engine) rozhodne, **kedy** vstúpiť; keď má config `trendFilter` iné než `off`, obal
`EntryFilterEngine` vstup pustí len v zadanom vzťahu k trendu:

* ``with``    — long len keď je zavretie nad EMA, short len pod ňou (s trendom),
* ``against`` — naopak (proti trendu, návrat k priemeru).

EMA má dĺžku `trendEmaLen` a počíta sa zo zavretí na `trendTF` minútach (0 = TF grafu); vyšší TF sa
skladá z barov grafu a do EMA ide až uzavretý bar. Predhistóriu dostane seedom pred prvým barom
(`Warmup.add_seeded`); kým nemá `trendEmaLen` barov, vstupy nepúšťa.

Obal je generický (nepozná stratégiu menom), platí pre market aj limit vstupy a nasadzujú ho adaptéry
ako najvnútornejší (pod potvrdenie sviečkou a typ orderu). Pri `off` sa engine nebalí. IBS a odnože
a Liquidity majú vlastné filtre trendu.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .engine import EngineOutput
from .orders import MarketContext, OrderAction
from .types import Bar, Direction
from .warmup import ema_bars

__all__ = ["TrendFilter", "EntryFilterFields", "ENTRY_FILTER_ENUMS", "ENTRY_FILTER_CONSTRAINTS",
           "ENTRY_FILTER_FIELD_NAMES", "entry_filter_params", "EntryFilterEngine", "wrap_entry_filter"]


class TrendFilter(str, Enum):
    OFF = "off"
    WITH = "with"        # len v smere trendu
    AGAINST = "against"  # len proti trendu


@dataclass
class EntryFilterFields:
    """Mixin polí configu. Pridáva sa ako ďalší predok configu stratégie."""

    trendFilter: TrendFilter = TrendFilter.OFF
    trendEmaLen: int = 200
    trendTF: int = 0


ENTRY_FILTER_FIELD_NAMES: frozenset[str] = frozenset({"trendFilter", "trendEmaLen", "trendTF"})
ENTRY_FILTER_ENUMS: dict[str, type] = {"trendFilter": TrendFilter}
ENTRY_FILTER_CONSTRAINTS: dict[str, tuple[float, float]] = {"trendEmaLen": (2, 1000), "trendTF": (0, 1440)}


def entry_filter_params(group: str) -> dict[str, dict[str, Any]]:
    """Popisy polí pre formulár webapp (do `params.py` stratégie)."""
    return {
        "trendFilter": dict(group=group, title="Filter trendu (EMA)",
                            tooltip="off = bez filtra; with = long len nad EMA a short len pod nou; against = naopak."),
        "trendEmaLen": dict(group=group, title="Filter trendu: dlzka EMA", tooltip="Klasika 50 / 100 / 200."),
        "trendTF": dict(group=group, title="Filter trendu: TF (min)",
                        tooltip="Na akom TF sa EMA pocita. 0 = TF grafu; 60 = hodinova, 240 = stvorhodinova."),
    }


class EntryFilterEngine:
    """Obal enginu: vstupy stratégie púšťa len v zadanom vzťahu k EMA (viď hlavičku modulu)."""

    def __init__(self, engine: Any, cfg: Any, chart_tf_minutes: int) -> None:
        self.engine = engine
        self.cfg = cfg
        self.mode = TrendFilter(cfg.trendFilter)
        self.n = int(cfg.trendEmaLen)
        chart = max(1, int(chart_tf_minutes))
        tf = int(cfg.trendTF) or chart
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
        warmup = getattr(engine, "warmup", None)
        if warmup is not None and hasattr(warmup, "add_seeded"):
            warmup.add_seeded(f"filter trendu EMA {self.n} na {tf}m", ema_bars(self.n), tf, self._seed)

    def __getattr__(self, name: str) -> Any:   # inst, required_history, warmup, final_drawings…
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
        if self.ema is None:
            return False
        above = close > self.ema
        long = direction is Direction.LONG
        return (above == long) if self.mode is TrendFilter.WITH else (above != long)

    def on_bar(self, bar: Bar, htf: Any = None, ctx: MarketContext | None = None) -> EngineOutput:
        self._push(bar)
        out = self.engine.on_bar(bar, htf, ctx)
        out.orders = [o for o in out.orders
                      if not (o.action is OrderAction.ENTRY and o.plan is not None
                              and not self.allows(o.plan.direction, bar.close))]
        return out


def wrap_entry_filter(engine: Any, cfg: Any, chart_tf_minutes: int) -> Any:
    """Engine obalený filtrom trendu, keď to config chce; inak ten istý engine."""
    t = getattr(cfg, "trendFilter", None)
    if t is None or not hasattr(cfg, "trendTF") or TrendFilter(t) is TrendFilter.OFF:
        return engine
    return EntryFilterEngine(engine, cfg, chart_tf_minutes)
