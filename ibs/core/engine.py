"""`IBSEngine` — jeden vstupný bod pre obe platformy.

Spája hodiny, detekciu zón a stavový automat do jediného volania ``on_bar``.
Adaptéry (Freqtrade, MultiCharts) aj diagnostické nástroje idú cez toto, aby
nemohli logiku poskladať zakaždým trochu inak.

Engine je **čistý**: žiadne I/O, žiadny `print`, žiadny globálny stav. Všetko,
čo si pamätá, je v `self`, takže je deterministický a testovateľný.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .clock import ClockState, SessionClock
from .config import IBSConfig
from .drawing import DrawCommand
from .history import BarHistory
from .statemachine import MarketContext, OrderIntent, StateEvent, StateMachine
from .types import Bar, HTFWindow, InstrumentSpec
from .zones import Zone, ZoneBook, detect_sd_pattern

__all__ = ["EngineOutput", "IBSEngine"]


@dataclass
class EngineOutput:
    """Čo engine na danom bare zistil. Nič z toho sám nevykonáva."""

    orders: list[OrderIntent] = field(default_factory=list)
    drawings: list[DrawCommand] = field(default_factory=list)
    events: list[StateEvent] = field(default_factory=list)
    new_zone: Zone | None = None
    clock: ClockState | None = None
    #: Pine `tradeWindowJustClosed` — spúšťa `closeAtSessionEnd`.
    trade_window_just_closed: bool = False

    def __bool__(self) -> bool:
        return bool(self.orders or self.drawings or self.events or self.new_zone)


class IBSEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(
        self,
        cfg: IBSConfig,
        inst: InstrumentSpec,
        chart_tf_minutes: int,
    ) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = chart_tf_minutes

        self.clock = SessionClock(cfg)
        self.book = ZoneBook(cfg, inst, chart_tf_minutes)
        self.machine = StateMachine(cfg, inst, self.book)
        self.history = BarHistory(
            maxlen=max(cfg.imbLookback, cfg.slLookback, cfg.volSmaLen, cfg.engSizeAvgLen) + 64,
            atr_len=cfg.atrLen,
        )

        #: Pine `inTradeWindow[1]` — na detekciu konca seansy.
        self._was_in_trade_window = False

    # ------------------------------------------------------------------ #

    def on_bar(
        self,
        bar: Bar,
        htf: HTFWindow | None = None,
        ctx: MarketContext | None = None,
        *,
        atr: float | None = None,
    ) -> EngineOutput:
        """Spracuje jeden uzavretý bar.

        `htf` sa odovzdáva **len na bare, kde sa práve uzavrela nová perióda
        detekčného TF** — vtedy Pine hľadá pattern (`first5mTick`). Inokedy `None`.
        """
        self.history.append(bar)
        state = self.clock.state(bar.time)
        # Parametre v jednotke `atr` sa prepocitavaju z ATR grafoveho TF. Volajuci ho
        # moze prebit, inak sa berie z vlastnej historie - inak by tie prahy vysli 0.
        if atr is None:
            atr = self.history.atr
        was_in_window = self._was_in_trade_window

        if ctx is None:
            ctx = MarketContext(in_trade_window=state.in_trade_window)
        else:
            ctx.in_trade_window = state.in_trade_window

        out = EngineOutput(clock=state)

        if htf is not None and state.in_zone_window:
            pattern = detect_sd_pattern(htf, self.cfg, self.inst, atr=atr)
            if pattern is not None:
                zone = self.book.create_from_pattern(pattern, now_ms=bar.time)
                if zone is not None:
                    zone.created_bar_index = self.history.bar_index
                    out.new_zone = zone
                    out.drawings.extend(zone.boxes(self.chart_tf_minutes * 60_000))

        out.orders = self.machine.on_bar(bar, self.history, ctx, atr=atr)
        out.events = list(self.machine.events)

        self._was_in_trade_window = state.in_trade_window
        out.trade_window_just_closed = was_in_window and not state.in_trade_window
        return out

    # ------------------------------------------------------------------ #

    def zones_at(self, ts_ms: int) -> list[Zone]:
        return self.book.active(ts_ms)
