"""Životný cyklus zóny STATE 0 → 5 — replika Pine riadkov 1534–2270.

Toto je srdce stratégie a zároveň dôvod, prečo sa jadro nedá vektorizovať: každý
krok závisí od predchádzajúceho **a** od toho, čo sa medzitým stalo s ostatnými
zónami (opačná pozícia, opačný čakajúci order, denný limit výhier).

Priebeh IMB modelu:

  ``0`` cena sa dotkne zóny a hľadá sa v nej gap
  ``1`` gap nájdený, čaká sa na výstup z zóny        (max `state1MaxBars`)
  ``2`` cena vyšla, čaká sa na potvrdenie zavretím   (max `state2MaxBars`)
  ``3`` potvrdené, čaká sa na retest vstupnej ceny   (max `state3MaxBars`)
  ``4`` položí sa order
  ``5`` čaká sa na vyplnenie                          (max `state5MaxBars`)

Pin Bar a Engulfing model preskakujú rovno z ``0`` do ``4``.

Engine dostáva len uzavreté bary, takže Pine ``barstate.isconfirmed`` je tu vždy
splnené a v podmienkach sa už neobjavuje.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum

from .config import IBSConfig
from .drawing import (
    PAL,
    DrawBox,
    DrawCommand,
    DrawDelete,
    DrawKind,
    DrawLabel,
    DrawUpdate,
    LabelStyle,
    with_alpha,
)
from .history import BarHistory
from .risk import TradePlan, build_trade_plan, swing_stop_loss
from .ta.imbalance import find_imbalance
from .ta.patterns import is_engulfing, is_pin_bar
from .types import Bar, Direction, InstrumentSpec, OrderType
from .zones import Zone, ZoneBook, ZoneSource

__all__ = [
    "ZoneState",
    "OrderAction",
    "OrderIntent",
    "StateEvent",
    "MarketContext",
    "StateMachine",
]


class ZoneState(IntEnum):
    INVALID = -1
    WAITING = 0
    GAP_FOUND = 1
    LEFT_ZONE = 2
    CONFIRMED = 3
    READY = 4
    ORDER_PENDING = 5


class OrderAction(str, Enum):
    ENTRY = "entry"
    CANCEL = "cancel"
    #: Zavri otvorenu poziciu za trhovu cenu - Pine `strategy.close(immediately=true)`.
    CLOSE = "close"


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """Čo má adaptér spraviť. Engine sám nikdy neobchoduje."""

    action: OrderAction
    order_id: str
    zone_uid: int
    direction: Direction | None = None
    plan: TradePlan | None = None
    order_type: OrderType = OrderType.LIMIT
    reason: str = ""


@dataclass(frozen=True, slots=True)
class StateEvent:
    """Záznam prechodu — pre logy, diagnostiku a golden testy."""

    ts_ms: int
    zone_uid: int
    from_state: int
    to_state: int
    reason: str = ""


@dataclass
class MarketContext:
    """Čo o svete engine sám nevie a musí mu to povedať adaptér."""

    in_trade_window: bool
    #: > 0 long, < 0 short, 0 flat — Pine `strategy.position_size`
    position_size: float = 0.0
    #: Pine `dailyWinLimitReached`
    daily_win_limit_reached: bool = False
    #: Pine `marketBias`: +1 bullish, -1 bearish, 0 neurčené
    market_bias: int = 0
    #: id orderov, ktoré u brokera práve reálne bežia (Pine `strategy.opentrades`)
    open_order_ids: frozenset[str] = field(default_factory=frozenset)


class StateMachine:
    """Posúva všetky zóny o jeden bar. Stav drží v samotných `Zone` objektoch."""

    def __init__(self, cfg: IBSConfig, inst: InstrumentSpec, book: ZoneBook) -> None:
        self.cfg = cfg
        self.inst = inst
        self.book = book
        self.events: list[StateEvent] = []
        #: Pine `box.set_*` volania z tohto baru — engine ich pripojí k výstupu.
        self.drawings: list[DrawCommand] = []

    # ------------------------------------------------------------------ #

    def on_bar(
        self,
        bar: Bar,
        history: BarHistory,
        ctx: MarketContext,
        *,
        atr: float = 0.0,
    ) -> list[OrderIntent]:
        intents: list[OrderIntent] = []
        self.events = []
        self.drawings = []

        self._expire(bar)

        for zone in list(self.book.zones):
            if not self._is_active(zone):
                continue
            intents.extend(self._advance(zone, bar, history, ctx, atr))

        return intents

    def cut_forming_zones(self, bar: Bar) -> None:
        """Pine riadky 2271-2288 — koniec KAŽDEJ seansy utne zóny v STATE 0-3.

        Zóna, ktorá sa ešte len formuje alebo čaká na potvrdenie, nemá ešte žiadny
        order, a preto ju nechytí ani kontrola v STATE 4/5, ani `close_session`
        (tá beží až po poslednej seanse dňa). Bez tohto by taká zóna prežila medzeru
        medzi dvoma seansami a obchodovala sa v tej nasledujúcej — box sa na grafe
        tiahol cez viacero seáns a vznikli obchody, ktoré TradingView nemá.

        STATE 4 a 5 sa tu zámerne nechávajú bokom, tie majú vlastnú logiku.
        """
        for z in list(self.book.zones):
            if 0 <= int(z.state) <= 3:
                self._invalidate(z, bar, "koniec seansy")

    def close_session(self, bar: Bar, ctx: MarketContext) -> list[OrderIntent]:
        """Pine riadky 2291-2318 - koniec poslednej seansy dna zmete vsetko zo stola.

        Zrusia sa cakajuce ordre, zavrie sa otvorena pozicia a vsetky zony sa
        invaliduju, aby nepresahovali do dalsieho dna. Volat az po `on_bar`.

        Dlho to nikomu nechybalo: pri `rrRatio = 1` a zapnutom trailingu sa obchody
        rozhodli v ramci minut a ziadny sa konca seansy nedozil. Pri RR 2,5 s vypnutym
        trailingom uz ano - a bez tohto by obchod bezal aj cez noc do dalsieho dna.
        """
        intents: list[OrderIntent] = []
        for z in list(self.book.zones):
            if not (0 <= int(z.state) <= 5):
                continue
            if int(z.state) >= 1:
                intents.append(
                    OrderIntent(
                        OrderAction.CANCEL, z.order_id, z.uid, reason="koniec seansy"
                    )
                )
                if int(z.state) == 5 and z.order_id in ctx.open_order_ids:
                    intents.append(
                        OrderIntent(
                            OrderAction.CLOSE, z.order_id, z.uid, reason="SESSION_END"
                        )
                    )
            self._invalidate(z, bar, "koniec seansy")
        return intents

    # ------------------------------------------------------------------ #

    def _expire(self, bar: Bar) -> None:
        """Pine riadky 665–681 — samostatný prechod PRED hlavným cyklom.

        Zóna, ktorej vypršala platnosť (`zoneValidHours`) a ešte nebola použitá, sa
        označí ako `used`. Tým vypadne z aktívnej množiny, lebo `_is_active` púšťa
        ďalej `used` zóny len v stavoch 2–5.

        Bez toho zóny v STATE 0 žijú donekonečna a hromadia sa — v porovnaní
        s TradingView to na BTCUSDT.P znamenalo 7× viac Pin Bar vstupov a 6× viac
        SKIP-ov (viď docs/GOLDEN_binance_2026-08-24.md).
        """
        for z in self.book.zones:
            if not z.used and bar.time >= z.expires_ms:
                z.used = True
                self.events.append(
                    StateEvent(bar.time, z.uid, z.state, z.state, "zona expirovala")
                )
                self.drawings.extend(z.resize_on_invalidation(bar.time))

    @staticmethod
    def _is_active(z: Zone) -> bool:
        """Pine: ``(not used and st >= 0) or (used and 2 <= st <= 5)``."""
        if not z.used:
            return z.state >= ZoneState.WAITING
        return ZoneState.LEFT_ZONE <= z.state <= ZoneState.ORDER_PENDING

    def _transition(self, z: Zone, to: int, bar: Bar, reason: str = "") -> None:
        self.events.append(StateEvent(bar.time, z.uid, z.state, to, reason))
        z.state = to

    def _invalidate(self, z: Zone, bar: Bar, reason: str) -> None:
        self._transition(z, ZoneState.INVALID, bar, reason)
        z.used = True
        # Pine `resizeZoneOnInvalidation` — volá sa na KAŽDEJ ceste invalidácie.
        self.drawings.extend(z.resize_on_invalidation(bar.time))

    # ------------------------------------------------------------------ #

    def _advance(
        self,
        z: Zone,
        bar: Bar,
        history: BarHistory,
        ctx: MarketContext,
        atr: float,
    ) -> list[OrderIntent]:
        cfg = self.cfg
        intents: list[OrderIntent] = []

        if z.state == ZoneState.WAITING:
            self._state0(z, bar, history, atr)

        if cfg.enableImbEntry and ZoneState.GAP_FOUND <= z.state <= ZoneState.READY:
            intents += self._re_entry(z, bar, history, atr)

        if ZoneState.GAP_FOUND <= z.state <= ZoneState.ORDER_PENDING:
            self._mark_passed_through(z, bar)

        if z.state == ZoneState.GAP_FOUND:
            self._state1(z, bar, history)

        if z.state == ZoneState.LEFT_ZONE:
            self._state2(z, bar, history, atr)

        if z.state == ZoneState.CONFIRMED:
            self._state3(z, bar, history, ctx)

        if z.state == ZoneState.READY:
            intents += self._state4(z, bar, history, ctx, atr)

        if z.state == ZoneState.ORDER_PENDING:
            intents += self._state5(z, bar, history, ctx)

        return intents

    # ---- STATE 0 ------------------------------------------------------- #

    def _state0(self, z: Zone, bar: Bar, history: BarHistory, atr: float) -> None:
        cfg = self.cfg
        long = z.direction is Direction.LONG

        if not z.touched:
            # Pine `correctApproach` - dotyk musi prist zo spravnej strany.
            approach = (
                (bar.low <= z.top and bar.high >= z.top)
                if long
                else (bar.high >= z.bot and bar.low <= z.bot)
            )
            if approach:
                z.touched = True
                z.touched_bar_index = history.bar_index

        if not z.touched:
            return

        in_zone = bar.high >= z.bot and bar.low <= z.top
        invalidated = (bar.low < z.bot) if long else (bar.high > z.top)

        if cfg.enablePinBarEntry:
            if in_zone and is_pin_bar(bar, z.direction, cfg, self.inst, atr=atr):
                self._arm_from_candle(z, bar, history, atr)
                return
            if invalidated:
                self._invalidate(z, bar, "PIN BAR: cena presla zonou")
                return

        if cfg.enableEngulfingEntry and z.state == ZoneState.WAITING:
            # „Okno trpezlivosti": prvych engTouchWindowBars barov po dotyku sa zona
            # pre Engulfing NEinvaliduje - velka outlier sviecka potrebuje viac barov.
            within_window = z.touched_bar_index is None or (
                history.bar_index - z.touched_bar_index
            ) <= cfg.engTouchWindowBars
            if in_zone and is_engulfing(history, z.direction, cfg, self.inst, atr=atr):
                self._arm_from_candle(z, bar, history, atr)
                return
            if not within_window and invalidated:
                self._invalidate(z, bar, "ENGULFING: cena presla zonou")
                return

        if cfg.enableImbEntry and cfg.enableGapDetection and z.state == ZoneState.WAITING:
            hit = find_imbalance(
                history, z.top, z.bot, z.direction, cfg, self.inst,
                zone_created_bar_index=z.created_bar_index, atr=atr,
            )
            if hit is not None:
                z.imb_body_top = hit.body_top
                z.imb_body_bot = hit.body_bot
                z.imb_open = hit.open
                z.imb_high = hit.high
                z.imb_low = hit.low
                z.imb_bar_index = hit.bar_index
                z.state_bar_index = history.bar_index
                self._transition(z, ZoneState.GAP_FOUND, bar, f"gap @ {hit.bar_index}")
            elif invalidated:
                self._invalidate(z, bar, "IMB: cena presla zonou")

    def _arm_from_candle(self, z: Zone, bar: Bar, history: BarHistory, atr: float) -> None:
        """Pin Bar / Engulfing: zóna ide rovno do STATE 4 a SL je z tejto sviečky."""
        buffer = self.cfg.slBufferTicks.resolve(self.inst, price=bar.close, atr=atr)
        z.imb_body_top = bar.body_top
        z.imb_body_bot = bar.body_bottom
        z.imb_open = bar.close  # vstup je na zavretí, nie na otvorení
        z.imb_high = bar.high
        z.imb_low = bar.low
        z.imb_bar_index = history.bar_index
        z.order_sl = (bar.low - buffer) if z.direction is Direction.LONG else (bar.high + buffer)
        z.state_bar_index = history.bar_index
        z.state_time_ms = bar.time
        self._transition(z, ZoneState.READY, bar, "pattern entry")

    # ---- RE-ENTRY ------------------------------------------------------ #

    def _re_entry(self, z: Zone, bar: Bar, history: BarHistory, atr: float) -> list[OrderIntent]:
        """Pine riadky 1710–1770 — cena sa vrátila a našiel sa INÝ gap než ten,
        na ktorom už beží order. Starý order sa zruší a zóna sa vráti do STATE 1."""
        cfg = self.cfg
        long = z.direction is Direction.LONG

        re_touch = (
            (bar.low <= z.top and bar.high >= z.top)
            if long
            else (bar.high >= z.bot and bar.low <= z.bot)
        )
        if not (re_touch and cfg.enableGapDetection):
            return []

        hit = find_imbalance(
            history, z.top, z.bot, z.direction, cfg, self.inst,
            zone_created_bar_index=z.created_bar_index, atr=atr,
        )
        if hit is None or hit.bar_index == z.imb_bar_index:
            return []

        z.imb_body_top = hit.body_top
        z.imb_body_bot = hit.body_bot
        z.imb_open = hit.open
        z.imb_high = hit.high
        z.imb_low = hit.low
        z.imb_bar_index = hit.bar_index
        z.filled = False
        z.pending_invalid = False
        z.ordered = False
        z.order_sl = None
        z.entry_done = False
        z.used = False
        z.state_bar_index = history.bar_index
        self._transition(z, ZoneState.GAP_FOUND, bar, "re-entry: iny gap")

        return [
            OrderIntent(OrderAction.CANCEL, z.order_id, z.uid, reason="re-entry"),
        ]

    # ---- pending invalidation ------------------------------------------ #

    def _mark_passed_through(self, z: Zone, bar: Bar) -> None:
        """Pine: cena prešla zónou naskrz — zóna sa označí, ale hneď nezaniká."""
        long = z.direction is Direction.LONG
        passed = (
            (bar.high >= z.top and bar.low < z.bot)
            if long
            else (bar.low <= z.bot and bar.high > z.top)
        )
        if passed and not z.pending_invalid:
            z.pending_invalid = True

    # ---- STATE 1-3 ------------------------------------------------------ #

    def _bars_in_state(self, z: Zone, history: BarHistory) -> int:
        if z.state_bar_index is None:
            z.state_bar_index = history.bar_index
        return history.bar_index - z.state_bar_index

    def _state1(self, z: Zone, bar: Bar, history: BarHistory) -> None:
        if self._bars_in_state(z, history) > self.cfg.state1MaxBars:
            self._invalidate(z, bar, "STATE1 timeout")
            return

        long = z.direction is Direction.LONG
        left = (bar.high > z.top and bar.low <= z.top) if long else (bar.low < z.bot and bar.high >= z.bot)
        if left:
            z.state_bar_index = history.bar_index
            z.state_time_ms = bar.time
            z.used = True
            self._transition(z, ZoneState.LEFT_ZONE, bar, "vystup zo zony")

    def _state2(self, z: Zone, bar: Bar, history: BarHistory, atr: float) -> None:
        if self._bars_in_state(z, history) > self.cfg.state2MaxBars:
            self._invalidate(z, bar, "STATE2 timeout")
            return

        confirm = self.cfg.state2ConfirmTicks.resolve(self.inst, price=bar.close, atr=atr)
        if z.direction is Direction.LONG:
            ok = z.imb_body_top is not None and bar.close > z.imb_body_top + confirm
        else:
            ok = z.imb_body_bot is not None and bar.close < z.imb_body_bot - confirm
        if ok:
            z.state_bar_index = history.bar_index
            self._transition(z, ZoneState.CONFIRMED, bar, "potvrdene zavretim")

    def _state3(self, z: Zone, bar: Bar, history: BarHistory, ctx: MarketContext) -> None:
        if self._bars_in_state(z, history) > self.cfg.state3MaxBars:
            self._invalidate(z, bar, "STATE3 timeout")
            return

        if z.imb_open is None or not ctx.in_trade_window:
            return

        retest = bar.low <= z.imb_open if z.direction is Direction.LONG else bar.high >= z.imb_open
        if retest:
            z.state_bar_index = history.bar_index
            z.state_time_ms = bar.time
            self._transition(z, ZoneState.READY, bar, "retest vstupnej ceny")

    # ---- STATE 4 -------------------------------------------------------- #

    def _state4(
        self, z: Zone, bar: Bar, history: BarHistory, ctx: MarketContext, atr: float
    ) -> list[OrderIntent]:
        cfg = self.cfg

        if ctx.daily_win_limit_reached:
            self._invalidate(z, bar, "MAX DAILY")
            return []

        if not ctx.in_trade_window:
            self._invalidate(z, bar, "mimo trade okna")
            return [OrderIntent(OrderAction.CANCEL, z.order_id, z.uid, reason="mimo trade okna")]

        # Pine: iná zóna už obchoduje ten istý gap -> táto sa zahodí.
        if not z.ordered:
            for other in self.book.zones:
                if other is z or not other.ordered:
                    continue
                if other.state not in (ZoneState.READY, ZoneState.ORDER_PENDING):
                    continue
                same_bar = other.imb_bar_index == z.imb_bar_index
                same_open = z.imb_open is not None and other.imb_open == z.imb_open
                if same_bar or same_open:
                    self._invalidate(z, bar, "duplicitny gap")
                    return []

        if z.ordered:
            if z.state != ZoneState.ORDER_PENDING:
                z.state_bar_index = history.bar_index
                z.state_time_ms = bar.time
                self._transition(z, ZoneState.ORDER_PENDING, bar, "order uz zadany")
            return []

        entry = z.imb_open
        if entry is None:
            self._invalidate(z, bar, "chyba vstupna cena")
            return []

        if z.order_sl is not None:
            stop = z.order_sl  # Pin Bar / Engulfing si SL priniesli zo STATE 0
        else:
            stop = swing_stop_loss(
                history, z.direction, cfg, self.inst,
                zone_top=z.top, zone_bot=z.bot, atr=atr,
            )

        plan = build_trade_plan(z.direction, entry, stop, cfg, self.inst)

        skip = self._skip_reason(z, bar, history, ctx, plan=plan, atr=atr)
        if skip:
            self._invalidate(z, bar, f"SKIP: {skip}")
            self._draw_label(
                z, bar, DrawKind.SKIP,
                f"SKIP ({'LONG' if z.direction is Direction.LONG else 'SHORT'})\n{skip}",
                color=with_alpha(PAL.GRAY.value, 20), bubble=True,
            )
            return []

        use_market = z.order_sl is not None and cfg.pbEngOrderType is OrderType.MARKET

        z.ordered = True
        z.order_sl = stop
        z.state_bar_index = history.bar_index
        self._transition(z, ZoneState.ORDER_PENDING, bar, "order zadany")
        self._draw_trade_boxes(z, bar, plan)

        return [
            OrderIntent(
                OrderAction.ENTRY,
                z.order_id,
                z.uid,
                direction=z.direction,
                plan=plan,
                order_type=OrderType.MARKET if use_market else OrderType.LIMIT,
            )
        ]

    # -- kreslenie ------------------------------------------------------- #

    def _draw_trade_boxes(self, z: Zone, bar: Bar, plan: TradePlan) -> None:
        """Pine riadky 2085–2099 — dva vyplnené bloky rozdelené na úrovni entry.

        Zelený je smerom k TP (reward), červený k SL (risk); funguje rovnako pre
        LONG aj SHORT, box sa len položí na správnu stranu. Pravý okraj je vopred
        `state5MaxBars * 3` barov dopredu (Pine `lineEnd`) a keď sa obchod zavrie,
        zmenší sa na aktuálny bar — viď `_close_trade_boxes`.
        """
        step = self.book.step_ms
        right = bar.time + self.cfg.state5MaxBars * 3 * step
        for kind, price, col in (
            (DrawKind.TP_BOX, plan.take_profit, PAL.STRONG.value),
            (DrawKind.SL_BOX, plan.stop_loss, PAL.LONG.value),
        ):
            self.drawings.append(
                DrawBox(
                    kind=kind,
                    x1_ms=bar.time,
                    y1=max(plan.entry, price),
                    x2_ms=right,
                    y2=min(plan.entry, price),
                    border_color=with_alpha(col, 100),
                    fill_color=with_alpha(col, 70),
                    border_width=0,
                    obj_id=f"z{z.uid}.{kind.value}",
                    zone_uid=z.uid,
                )
            )

    def _close_trade_boxes(self, z: Zone, bar: Bar) -> None:
        """Pine riadky 2231–2233 — po zavretí obchodu box končí na aktuálnom bare."""
        for kind in (DrawKind.TP_BOX, DrawKind.SL_BOX):
            self.drawings.append(DrawUpdate(f"z{z.uid}.{kind.value}", "x2_ms", bar.time))

    def _delete_trade_boxes(self, z: Zone) -> None:
        """Pine `deleteTradeBoxes` (riadok 1490) — order zrušený, boxy zmiznú."""
        for kind in (DrawKind.TP_BOX, DrawKind.SL_BOX):
            self.drawings.append(DrawDelete(f"z{z.uid}.{kind.value}"))

    def _draw_label(
        self, z: Zone, bar: Bar, kind: DrawKind, text: str, *, color: str, bubble: bool
    ) -> None:
        """Štítok nad/pod sviečkou. Pine ho pri LONG dáva pod low, pri SHORT nad high."""
        long = z.direction is Direction.LONG
        off = self.inst.tick_size * 10
        self.drawings.append(
            DrawLabel(
                kind=kind,
                x_ms=bar.time,
                y=bar.low - off if long else bar.high + off,
                text=text,
                color="#ffffff" if bubble else color,
                style=(LabelStyle.UP if long else LabelStyle.DOWN) if bubble else LabelStyle.NONE,
                above=not long,
                bg_color=color if bubble else None,
                obj_id=f"z{z.uid}.{kind.value}.{bar.time}",
                zone_uid=z.uid,
            )
        )

    def _skip_reason(
        self,
        z: Zone,
        bar: Bar,
        history: BarHistory,
        ctx: MarketContext,
        *,
        plan: TradePlan | None = None,
        atr: float = 0.0,
    ) -> str | None:
        """Pine `canTrade` — poradie dôvodov je zachované, lebo sa zobrazuje v SKIP labeli.

        Za Pine dôvodmi je jeden navyše, `minSlDistance` (rozšírenie portu, defaultne
        vypnuté) — ide až posledný, aby sa poradie Pine labelov nezmenilo.
        """
        cfg = self.cfg
        long = z.direction is Direction.LONG

        if not cfg.enableTrading:
            return "OBCHODOVANIE VYPNUTE"

        opposite_open = (long and ctx.position_size < 0) or (not long and ctx.position_size > 0)
        if opposite_open:
            return "OPACNA POZICIA"

        for other in self.book.zones:
            if (
                other is not z
                and other.state == ZoneState.ORDER_PENDING
                and other.direction is not z.direction
                and not other.filled
            ):
                return "OPACNY ORDER UZ CAKA"

        if cfg.useStructureFilter:
            wanted = 1 if long else -1
            if ctx.market_bias != wanted:
                return "STRUKTURA NESEDI"

        if cfg.useVolumeFilter and cfg.volumeFilterBlockTrading and z.source is ZoneSource.SD:
            vol_sma = history.sma_volume(cfg.volSmaLen)
            if not (bar.volume >= cfg.volMultiplier * vol_sma):
                return "VOLUME NEDOSTATOCNY"

        if not cfg.tradeDirection.allows(z.direction):
            return "SMER VYPNUTY"

        if plan is not None:
            min_sl = cfg.minSlDistance.resolve(self.inst, price=plan.entry, atr=atr)
            if min_sl > 0 and plan.sl_distance < min_sl:
                return "SL PRILIS TESNY"

        return None

    # ---- STATE 5 -------------------------------------------------------- #

    def _state5(
        self, z: Zone, bar: Bar, history: BarHistory, ctx: MarketContext
    ) -> list[OrderIntent]:
        intents: list[OrderIntent] = []
        bars_waiting = self._bars_in_state(z, history)

        running_now = z.order_id in ctx.open_order_ids

        if not z.filled and not running_now:
            timed_out = bars_waiting >= self.cfg.state5MaxBars
            if timed_out or not ctx.in_trade_window:
                self._invalidate(z, bar, "EXPIRED" if timed_out else "koniec seansy")
                if timed_out:
                    self._draw_label(
                        z, bar, DrawKind.EXPIRED, f"EXPIRED\nb={bars_waiting}",
                        color=PAL.AMBER.value, bubble=True,
                    )
                z.entry_done = False
                return [
                    OrderIntent(
                        OrderAction.CANCEL, z.order_id, z.uid,
                        reason="EXPIRED" if timed_out else "koniec seansy",
                    )
                ]
            return []

        if z.filled and not running_now and not z.trade_boxes_closed:
            # Pine 2231-2233: obchod sa zavrel (TP/SL). Boxy ostavaju ako historicky
            # zaznam, len sa im utne pravy okraj na bar, kde sa to naozaj stalo.
            z.trade_boxes_closed = True
            self._close_trade_boxes(z, bar)

        if not z.filled and running_now:
            z.filled = True
            self.events.append(StateEvent(bar.time, z.uid, z.state, z.state, "FILLED"))

            # Pine 2185 — vyplnením orderu sa zóna vizuálne uzavrie. Stav sa NEmení,
            # je to len rez boxu; `pending_invalid` je zóna, cez ktorú už cena prešla.
            if self.cfg.invalidateOnFill or z.pending_invalid:
                self.drawings.extend(z.resize_on_invalidation(bar.time))

            # OCO: kto vyplnil prvý, ten vypína opačné čakajúce ordery.
            for other in self.book.zones:
                if (
                    other is not z
                    and other.state == ZoneState.ORDER_PENDING
                    and other.direction is not z.direction
                    and not other.filled
                ):
                    self._invalidate(other, bar, "ZRUSENY (OCO)")
                    self._delete_trade_boxes(other)  # Pine 2200
                    other.entry_done = False
                    intents.append(
                        OrderIntent(OrderAction.CANCEL, other.order_id, other.uid, reason="OCO")
                    )

        return intents
