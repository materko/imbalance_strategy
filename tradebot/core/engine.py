"""Kontrakt engine-u stratégie — jedno volanie na uzavretý bar grafu.

Adaptéry (Freqtrade, MultiCharts) a webapp pracujú len s týmto rozhraním; vnútro
stratégie (stavový automat, zóny, indikátory) je ich vec. Engine je **čistý**:
žiadne I/O, žiadny globálny stav, všetko v `self`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .drawing import DrawCommand
from .orders import MarketContext, OrderIntent, StateEvent
from .types import Bar, InstrumentSpec

__all__ = ["EngineOutput", "Engine"]


@dataclass
class EngineOutput:
    """Čo engine na danom bare zistil. Nič z toho sám nevykonáva."""

    orders: list[OrderIntent] = field(default_factory=list)
    drawings: list[DrawCommand] = field(default_factory=list)
    events: list[StateEvent] = field(default_factory=list)
    #: Na tomto bare sa zatvorilo všetko otvorené (koniec seansy a pod.).
    close_session: bool = False

    def __bool__(self) -> bool:
        return bool(self.orders or self.drawings or self.events)


@runtime_checkable
class Engine(Protocol):
    """Bar-by-bar engine. `on_bar` sa volá presne raz na každý uzavretý bar grafu.

    `htf` je to, čo stratégii dodá jej `htf_feeder` (IBS: okno štyroch barov detekčného
    TF na bare, kde sa práve uzavrela nová perióda), inak `None`.
    """

    inst: InstrumentSpec
    chart_tf_minutes: int
    #: Koľko barov histórie treba, kým sú signály platné (Freqtrade `startup_candle_count`).
    required_history: int

    def on_bar(self, bar: Bar, htf: Any | None = None, ctx: MarketContext | None = None) -> EngineOutput: ...

    def final_drawings(self, bar: Bar) -> list[DrawCommand]: ...
