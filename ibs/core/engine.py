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
from .ta.elliott import ElliottWaves
from .ta.liquidity import LiquiditySweep
from .ta.sr import SupportResistance
from .ta.structure import MarketStructure
from .types import Bar, Direction, HTFWindow, InstrumentSpec
from .zones import Zone, ZoneBook, ZoneSource, detect_sd_pattern

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
    #: Na tomto bare sa zatvorilo všetko otvorené — Pine sekcia CLOSE AT SESSION END.
    close_session: bool = False

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
        self.structure = MarketStructure(cfg, inst)
        self.sr = SupportResistance(cfg, inst)
        self.liquidity = LiquiditySweep(cfg, inst)
        self.elliott = ElliottWaves(cfg, inst, chart_tf_minutes * 60_000)
        self.history = BarHistory(
            maxlen=max(cfg.imbLookback, cfg.slLookback, cfg.volSmaLen, cfg.engSizeAvgLen) + 64,
            atr_len=cfg.atrLen,
        )

        #: Pine `inTradeWindow[1]` — na detekciu konca seansy.
        self._was_in_trade_window = False

    # ------------------------------------------------------------------ #

    def _spawn_sr_zones(self, touched: list[int], bar: Bar, out: EngineOutput) -> None:
        """Pine `f_maybeSpawnSrZone` (riadok 911).

        Keď úroveň PRVÝKRÁT dosiahne `srMinTouches`, vznikne z nej obchodovateľná
        zóna — ďalej ide rovnakým STATE 0–5 mechanizmom ako SD zóna. Smer je
        dynamický: cena nad úrovňou = support = LONG.
        """
        for idx in touched:
            if not 0 <= idx < len(self.sr.levels):
                continue
            lvl = self.sr.levels[idx]
            if lvl.zone_spawned or lvl.touches < self.cfg.srMinTouches:
                continue
            lo, hi = lvl.low, lvl.high
            if lo == hi:
                lo -= self.inst.tick_size * 2
                hi += self.inst.tick_size * 2
            direction = Direction.LONG if bar.close > (lo + hi) / 2 else Direction.SHORT
            zone = self.book.create_raw(direction, hi, lo, bar.time, ZoneSource.SR)
            zone.created_bar_index = self.history.bar_index
            lvl.zone_spawned = True
            out.drawings.extend(zone.boxes(self.chart_tf_minutes * 60_000))

    def _spawn_sweep_zones(self, sweeps, bar: Bar, out: EngineOutput) -> None:
        """Pine riadky 1198–1247 — fade po sweepe, obchod ide PROTI prepichnutiu."""
        for sw in sweeps:
            zone = self.book.create_raw(
                sw.direction, sw.top, sw.bot, bar.time, ZoneSource.LIQUIDITY
            )
            zone.created_bar_index = self.history.bar_index
            out.drawings.extend(zone.boxes(self.chart_tf_minutes * 60_000))

    def final_drawings(self, bar: Bar) -> list:
        """Objekty, ktoré Pine kreslí až na poslednom bare (`barstate.islast`).

        Zloženie S/R zhlukov závisí od aktuálnej ceny, takže priebežne by to
        znamenalo tisíce prekreslení. Adaptér to zavolá raz, keď dobehne.
        """
        return self.sr.render(bar) + self.elliott.render(bar, self.history)

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
        out.drawings.extend(state.backgrounds(bar.time, self.chart_tf_minutes * 60_000))
        # Market Structure beží vždy — `marketBias` z neho číta filter
        # `useStructureFilter`, ktorý je v referenčných profiloch vypnutý.
        out.drawings.extend(self.structure.on_bar(bar, self.history))
        ctx.market_bias = self.structure.bias

        # S/R zbiera dotyky priebežne, ale kreslí sa až v `final_drawings()` -
        # Pine to má na `barstate.islast`, lebo zloženie zhlukov závisí od ceny.
        touched = self.sr.on_bar(bar, self.history)
        if self.cfg.enableSrTrading and state.in_zone_window:
            self._spawn_sr_zones(touched, bar, out)

        liq_draw, sweeps = self.liquidity.on_bar(bar, self.history)
        out.drawings.extend(liq_draw)
        if state.in_zone_window:
            self._spawn_sweep_zones(sweeps, bar, out)

        self.elliott.on_bar(bar, self.history)

        if htf is not None and state.in_zone_window:
            pattern = detect_sd_pattern(htf, self.cfg, self.inst, atr=atr)
            if pattern is not None:
                zone = self.book.create_from_pattern(pattern, now_ms=bar.time)
                if zone is not None:
                    zone.created_bar_index = self.history.bar_index
                    out.new_zone = zone
                    out.drawings.extend(zone.boxes(self.chart_tf_minutes * 60_000))

        out.orders = self.machine.on_bar(bar, self.history, ctx, atr=atr)
        if (
            self.cfg.closeAtSessionEnd
            and state.no_more_sessions_today
            and not state.in_trade_window
        ):
            out.orders.extend(self.machine.close_session(bar, ctx))
            out.close_session = True
        # Pine `box.set_*` z tohto baru (zmenšenie pri invalidácii, prefarbenie).
        out.drawings.extend(self.machine.drawings)
        out.events = list(self.machine.events)

        self._was_in_trade_window = state.in_trade_window
        out.trade_window_just_closed = was_in_window and not state.in_trade_window
        return out

    # ------------------------------------------------------------------ #

    def zones_at(self, ts_ms: int) -> list[Zone]:
        return self.book.active(ts_ms)
