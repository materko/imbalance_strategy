"""Prevedie `IBSEngine` cez MultiCharts `CalcBar()` — bez závislosti na PowerLanguage.

Celá logika adaptéra je tu, aby sa dala testovať na obyčajnom Pythone. Trieda
`IBS_Signal` (v `signal.py`) už len prekladá volania na PowerLanguage .NET API
a nesmie obsahovať žiadne rozhodovanie.

### Prečo sa ordre posielajú znova každý bar
Toto je najväčší rozdiel oproti Pine aj Freqtrade. V Pine `strategy.entry` položí
order, ktorý **leží**, kým ho niekto nezruší. V MultiCharts platí order len na
nasledujúci bar — ak sa nepošle znova, ticho zmizne.

Runner preto drží množinu „živých" orderov a na každom bare vráti kompletný zoznam
toho, čo sa má poslať. `OrderIntent(CANCEL)` znamená jednoducho vypadnutie
z tej množiny, nie osobitné volanie.

### HTF okno
Zámerne sa nepoužíva `Data2` séria priamo, ale ten istý `htf_window_opens()` ako
vo Freqtrade — inak by sa obe platformy rozišli práve v tom mieste, ktoré nás
na TradingView stálo najviac času (viď docs/GOLDEN_binance_2026-08-24.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...core import (
    Bar,
    DrawCommand,
    HTFWindow,
    IBSConfig,
    IBSEngine,
    InstrumentSpec,
    MarketContext,
    SessionClock,
    htf_window_opens,
)
from ...core.risk import TradePlan
from ...core.statemachine import OrderAction, OrderIntent
from ...core.types import Direction

__all__ = ["LiveOrder", "MCRunner", "BarOutput"]


@dataclass(frozen=True, slots=True)
class LiveOrder:
    """Order, ktorý má tento bar ležať na trhu."""

    order_id: str
    zone_uid: int
    direction: Direction
    plan: TradePlan
    #: True = poslať ako market (Pin Bar / Engulfing s `pbEngOrderType=Market`)
    market: bool = False

    @property
    def is_long(self) -> bool:
        return self.direction is Direction.LONG


@dataclass
class BarOutput:
    """Čo má študia na tomto bare spraviť."""

    #: vstupné ordre, ktoré sa majú (znova) poslať
    entries: list[LiveOrder] = field(default_factory=list)
    #: výstupné ordre pre otvorenú pozíciu — (stop, limit) alebo None
    exit_plan: TradePlan | None = None
    drawings: list[DrawCommand] = field(default_factory=list)
    #: id orderov, ktoré tento bar prestali platiť — len na logovanie
    cancelled: list[str] = field(default_factory=list)


class MCRunner:
    """Jeden graf = jeden runner. Volaj `on_bar` presne raz za uzavretý bar."""

    def __init__(self, cfg: IBSConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = chart_tf_minutes
        self.step_ms = chart_tf_minutes * 60_000
        self.htf_ms = int(cfg.zoneDetectionTF) * 60_000

        self.engine = IBSEngine(cfg, inst, chart_tf_minutes)
        self.clock = SessionClock(cfg)

        #: HTF bary podľa otváracieho času — plní ich `feed_htf()` z Data2.
        self.htf_bars: dict[int, Bar] = {}
        self.htf_vol_sma: dict[int, float] = {}
        self._htf_volumes: list[float] = []

        self._prev_htf_open: int | None = None
        #: order_id -> LiveOrder; posiela sa znova, kým z množiny nevypadne
        self._live: dict[str, LiveOrder] = {}
        #: plán obchodu, ktorý sa práve drží (na SL/TP výstupy)
        self._open_plan: TradePlan | None = None
        self._open_id: str | None = None
        self.last_ts: int | None = None

    # ------------------------------------------------------------------ #
    # HTF
    # ------------------------------------------------------------------ #

    def feed_htf(self, bar: Bar) -> None:
        """Zaeviduje uzavretý bar detekčného TF (v MultiCharts `Data2`).

        Volá sa len keď sa HTF bar naozaj **uzavrel**; priebežné aktualizácie
        posledného baru by narušili `vol_sma`.
        """
        if bar.time in self.htf_bars:
            return
        self.htf_bars[bar.time] = bar
        self._htf_volumes.append(bar.volume)
        n = self.cfg.volSmaLen
        if len(self._htf_volumes) >= n:
            self.htf_vol_sma[bar.time] = sum(self._htf_volumes[-n:]) / n
        else:
            self.htf_vol_sma[bar.time] = 0.0

        # Držíme len toľko histórie, koľko treba na okno + SMA.
        keep = n + HTFWindow.REQUIRED_BARS + 8
        if len(self._htf_volumes) > keep:
            self._htf_volumes = self._htf_volumes[-keep:]
        if len(self.htf_bars) > keep:
            for old in sorted(self.htf_bars)[: len(self.htf_bars) - keep]:
                self.htf_bars.pop(old, None)
                self.htf_vol_sma.pop(old, None)

    def _window(self, ts_ms: int) -> HTFWindow | None:
        """Okno štyroch HTF barov — len na bare, kde začala nová HTF perióda."""
        htf_open = ts_ms // self.htf_ms * self.htf_ms
        is_new = self._prev_htf_open is not None and htf_open != self._prev_htf_open
        self._prev_htf_open = htf_open
        if not is_new:
            return None
        opens = htf_window_opens(ts_ms, self.step_ms, self.htf_ms)
        if any(o not in self.htf_bars for o in opens):
            return None
        return HTFWindow(
            tuple(self.htf_bars[o] for o in opens), self.htf_vol_sma.get(opens[0], 0.0)
        )

    # ------------------------------------------------------------------ #
    # hlavný krok
    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, *, position_size: float = 0.0) -> BarOutput:
        """Spracuje jeden uzavretý bar grafu.

        `position_size` je `self.MarketPosition` zo študie: > 0 long, < 0 short.
        Engine z toho číta `oppositeOpen` a OCO.
        """
        if self.last_ts is not None and bar.time <= self.last_ts:
            return BarOutput()  # MultiCharts vie zavolať CalcBar na tom istom bare
        self.last_ts = bar.time

        state = self.clock.state(bar.time)
        ctx = MarketContext(
            in_trade_window=state.in_trade_window,
            position_size=position_size,
            open_order_ids=frozenset(self._live),
        )
        out = self.engine.on_bar(bar, self._window(bar.time), ctx)

        result = BarOutput(drawings=list(out.drawings))
        for intent in out.orders:
            if intent.action is OrderAction.CANCEL:
                if self._live.pop(intent.order_id, None) is not None:
                    result.cancelled.append(intent.order_id)
                if intent.order_id == self._open_id:
                    self._open_plan = None
                    self._open_id = None
            elif intent.plan is not None:
                self._live[intent.order_id] = self._to_live(intent)

        # Pozícia je otvorená -> ordre na vstup už nemajú čo robiť, ale SL/TP áno.
        if position_size != 0.0:
            if self._open_plan is None:
                self._open_plan, self._open_id = self._adopt_open_plan()
            result.exit_plan = self._open_plan
        else:
            self._open_plan = None
            self._open_id = None
            result.entries = list(self._live.values())

        return result

    def _to_live(self, intent: OrderIntent) -> LiveOrder:
        from ...core.types import OrderType

        return LiveOrder(
            order_id=intent.order_id,
            zone_uid=intent.zone_uid,
            direction=intent.direction,
            plan=intent.plan,
            market=intent.order_type is OrderType.MARKET,
        )

    def _adopt_open_plan(self) -> tuple[TradePlan | None, str | None]:
        """Ktorý z čakajúcich orderov sa práve vyplnil.

        MultiCharts nepovie, ktorý order pozíciu otvoril — vie len `MarketPosition`.
        Ak čaká práve jeden, je to jednoznačné. Ak viac (LONG aj SHORT cez OCO),
        vezme sa ten, ktorý engine vytvoril ako posledný; ten druhý aj tak vzápätí
        dostane CANCEL cez OCO vetvu stavového automatu.
        """
        if not self._live:
            return None, None
        order_id, live = next(reversed(self._live.items()))
        return live.plan, order_id
