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

from ...core import Bar, DrawCommand, InstrumentSpec, MarketContext
from ...core.config import StrategyConfig
from ...core.orders import OrderAction, OrderIntent
from ...core.risk import TradePlan
from ...core.types import Direction
from ...strategies import StrategySpec, spec_for_config

__all__ = ["LiveOrder", "MCRunner", "BarOutput"]


@dataclass(frozen=True, slots=True)
class LiveOrder:
    """Order, ktorý má tento bar ležať na trhu."""

    order_id: str
    #: identita zdroja signálu (IBS: uid zóny)
    source_id: int
    direction: Direction
    plan: TradePlan
    #: True = poslať ako market (Pin Bar / Engulfing s `pbEngOrderType=Market`)
    market: bool = False

    @property
    def is_long(self) -> bool:
        return self.direction is Direction.LONG

    @property
    def zone_uid(self) -> int:
        """IBS názov toho istého poľa."""
        return self.source_id


@dataclass
class BarOutput:
    """Čo má študia na tomto bare spraviť."""

    #: vstupné ordre, ktoré sa majú (znova) poslať
    entries: list[LiveOrder] = field(default_factory=list)
    #: výstupné ordre pre otvorenú pozíciu — (stop, limit) alebo None
    exit_plan: TradePlan | None = None
    #: SL na tento bar. Rovná sa `exit_plan.stop_loss`, kým sa neaktivuje trailing;
    #: potom je posunutý za cenou, takže sa musí posielať zvlášť.
    exit_stop: float | None = None
    drawings: list[DrawCommand] = field(default_factory=list)
    #: id orderov, ktoré tento bar prestali platiť — len na logovanie
    cancelled: list[str] = field(default_factory=list)
    #: Pine `closeAtSessionEnd` — zavri otvorenú pozíciu za trhovú cenu.
    close_session: bool = False


class MCRunner:
    """Jeden graf = jeden runner. Volaj `on_bar` presne raz za uzavretý bar.

    Stratégia sa berie z registry podľa triedy configu (`spec_for_config`).
    """

    def __init__(self, cfg: StrategyConfig, inst: InstrumentSpec, chart_tf_minutes: int,
                 spec: StrategySpec | None = None) -> None:
        self.spec = spec or spec_for_config(cfg)
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = chart_tf_minutes
        self.step_ms = chart_tf_minutes * 60_000
        assert self.spec.engine_factory is not None, f"{self.spec.key}: chýba engine_factory"
        self.engine = self.spec.engine_factory(cfg, inst, chart_tf_minutes)

        #: feeder informatívneho TF (Data2; IBS: okno detekčného TF zón) alebo None —
        #: jedna implementácia pre Freqtrade aj MultiCharts, tu drží len minimum histórie.
        self.htf = self.spec.htf_feeder(cfg, chart_tf_minutes) if self.spec.htf_feeder else None
        if self.htf is not None and hasattr(self.htf, "limit_history"):
            self.htf.limit_history()
        self.htf_ms = getattr(self.htf, "htf_ms", None)
        #: order_id -> LiveOrder; posiela sa znova, kým z množiny nevypadne
        self._live: dict[str, LiveOrder] = {}
        #: plán obchodu, ktorý sa práve drží (na SL/TP výstupy)
        self._open_plan: TradePlan | None = None
        self._open_id: str | None = None
        #: Najlepšia cena od otvorenia pozície — vstup do trailingu.
        self._open_extreme: float = float("nan")
        self.last_ts: int | None = None

    # ------------------------------------------------------------------ #
    # HTF
    # ------------------------------------------------------------------ #

    def feed_htf(self, bar: Bar) -> None:
        """Zaeviduje uzavretý bar informatívneho TF (MultiCharts `Data2`) — viď `HTFFeeder.feed`.

        Stratégia bez informatívneho TF ho ignoruje.
        """
        if self.htf is not None:
            self.htf.feed(bar)

    @property
    def htf_bars(self) -> dict[int, Bar]:
        return self.htf.bars if self.htf is not None else {}

    @property
    def htf_vol_sma(self) -> dict[int, float]:
        return self.htf.vol_sma if self.htf is not None else {}

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

        # Obchodné okno si engine nastaví sám (IBS z vlastných hodín seáns); stratégia
        # bez seáns obchoduje vždy.
        ctx = MarketContext(
            in_trade_window=True,
            position_size=position_size,
            open_order_ids=frozenset(self._live),
        )
        htf = self.htf.window_for(bar.time) if self.htf is not None else None
        out = self.engine.on_bar(bar, htf, ctx)

        result = BarOutput(drawings=list(out.drawings), close_session=out.close_session)
        for intent in out.orders:
            if intent.action is OrderAction.CANCEL:
                if self._live.pop(intent.order_id, None) is not None:
                    result.cancelled.append(intent.order_id)
                if intent.order_id == self._open_id:
                    self._open_plan = None
                    self._open_id = None
                    self._open_extreme = float("nan")
            elif intent.plan is not None:
                self._live[intent.order_id] = self._to_live(intent)

        # Pozícia je otvorená -> ordre na vstup už nemajú čo robiť, ale SL/TP áno.
        if position_size != 0.0:
            if self._open_plan is None:
                self._open_plan, self._open_id = self._adopt_open_plan()
                self._open_extreme = float("nan")
            result.exit_plan = self._open_plan
            result.exit_stop = self._trailed_stop(bar)
        else:
            self._open_plan = None
            self._open_id = None
            self._open_extreme = float("nan")
            result.entries = list(self._live.values())

        return result

    def _trailed_stop(self, bar: Bar) -> float | None:
        """SL na tento bar — posunutý trailingom, ak už je aktivovaný.

        MultiCharts nemá ekvivalent Pine `trail_points`/`trail_offset`, takže sa stop
        prepočíta tu a pošle sa ako obyčajný stop order. Extrém sa aktualizuje pred
        výpočtom, rovnako ako vo Freqtrade aj v offline simulácii.
        """
        plan = self._open_plan
        if plan is None:
            return None
        if plan.trailing is None:
            return plan.stop_loss

        long = plan.direction is Direction.LONG
        best = bar.high if long else bar.low
        if self._open_extreme != self._open_extreme:  # NaN = prvý bar pozície
            self._open_extreme = plan.entry
        self._open_extreme = max(self._open_extreme, best) if long else min(
            self._open_extreme, best
        )
        return plan.trailing.stop_price(
            plan.direction, plan.entry, plan.stop_loss, self._open_extreme
        )

    def _to_live(self, intent: OrderIntent) -> LiveOrder:
        from ...core.types import OrderType

        return LiveOrder(
            order_id=intent.order_id,
            source_id=intent.source_id,
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
