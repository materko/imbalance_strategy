"""Engine tržnej štruktúry: potvrdené swingy → BOS / CHoCH → vstup, SL zo swingu, tri výstupy.

Celá myšlienka stojí na jednej vete, ktorá je zároveň to jediné, čo sa dá spraviť zle
tak, že si to nikto nevšimne:

    **Swing sa dá potvrdiť až `swingRight` barov potom, čo nastal.** Engine ho pred tým
    nesmie použiť ani na rozhodnutie, ani na SL, ani na kresbu.

Preto sa swing hľadá vždy na `history[swingRight]` — na bare, ktorý má za sebou `swingRight`
uzavretých barov — a nie na aktuálnom. Stráži to `test_structure_engine.py`
(`test_swing_sa_nepouzije_skor_nez_je_potvrdeny`); bez toho testu sa o tejto stratégii
nedá tvrdiť nič, lebo pohľad dopredu vyzerá v backteste ako edge.

Definície (`docs/sources/structure.pine` je zdroj pravdy):

* **swing high** — bar, ktorého `high` je **prísne vyššie** než `high` všetkých
  `swingLeft` barov vľavo a všetkých `swingRight` barov vpravo; swing low symetricky
  s `low`. Prísne `>` na oboch stranách znamená, že plató rovnakých maxím swing nie je.
* **BOS** — v stave `bullish` sa bar **zavrie** nad posledným potvrdeným swing high
  (v `bearish` pod swing low); stav ostáva, referenčná úroveň sa posúva.
* **CHoCH** — v stave `bullish` sa bar **zavrie** pod posledným potvrdeným swing low
  (v `bearish` nad swing high); stav sa otočí.

Rozhoduje **zatvorenie** baru, nie dotyk knôtom. Prerazená úroveň je spotrebovaná —
ďalšia udalosť tým smerom potrebuje nový potvrdený swing, inak by BOS „nastával" na
každom ďalšom bare.

Rodina výstupov je oproti IBS a demu nová: okrem SL a TP vie tento engine zavrieť obchod
na **ďalšej štruktúrnej udalosti v smere obchodu** (`exitMode = structure`) a po
**`maxBars` baroch** od signálu. Oboje ide cez generické `EngineOutput.close_session`
(Pine `strategy.close(immediately=true)`) — jadra sa to teda netýka.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import (
    DrawBg,
    DrawBox,
    DrawCommand,
    DrawKind,
    DrawLabel,
    DrawLine,
    DrawUpdate,
    LabelStyle,
    LineStyle,
    Palette,
    with_alpha,
)
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

from .config import EntryMode, ExitMode, SlMode, StructureConfig
from .drawing import ST_BOS, ST_CHOCH, ST_ENTRY, ST_LEVEL, ST_SWING_HIGH, ST_SWING_LOW

__all__ = ["StructureEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_SWING_COLOR = Palette.SLATE.value
_LEVEL_COLOR = Palette.GRAY.value + "b3"
_BOS_COLOR = Palette.STRONG.value
_CHOCH_COLOR = Palette.AMBER.value

#: Ako ďaleko dopredu siaha TP/SL box a úroveň swingu. Obchod ani úroveň nemajú vopred
#: známu dĺžku, takže je to len čitateľnosť grafu — úroveň sa navyše pri prerazení
#: skráti presne na bar, ktorý ju prerazil (`DrawUpdate`).
_BOX_BARS = 30
_LEVEL_BARS = 80

#: Kde leží TP order v režime `structure`. Obchod tam pevný cieľ **nemá** — končí na
#: štruktúrnej udalosti, stope alebo čase —, ale order sa poslať musí (MultiCharts ho
#: vyžaduje a NaN by v študii zhodilo `CalcBar`). 50 R je poistka, nie cieľ; preto sa
#: v tomto režime TP box ani nekreslí a analytika plánovaný RR správne nemá odkiaľ vziať.
_TP_BACKSTOP_R = 50.0


class StructureEngine:
    """Bar-by-bar engine. Volaj `on_bar` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: StructureConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = chart_tf_minutes
        self.step_ms = chart_tf_minutes * 60_000
        #: swing potrebuje L + R + 1 barov, ATR svoju dĺžku
        self.required_history = int(cfg.swingLeft) + int(cfg.swingRight) + 1 + int(cfg.atrLen) + 8
        self.history = BarHistory(maxlen=self.required_history + 8, atr_len=int(cfg.atrLen))
        self._tz = ZoneInfo(cfg.sessionTZ.value) if cfg.useSession else None

        #: 0 neutrálne, +1 bullish, -1 bearish — Pine `structState`
        self.state = 0
        #: posledný **potvrdený** swing high: úroveň, čas baru a či ho už close prerazil
        self._sw_high: float | None = None
        self._sw_high_ts: int = 0
        self._sw_high_used = False
        self._sw_low: float | None = None
        self._sw_low_ts: int = 0
        self._sw_low_used = False
        #: úroveň posledného prijatého swingu — referencia filtra šumu (`minSwingSize`)
        self._last_swing: float | None = None
        #: posledný vstupný order a bar, na ktorom vznikol (na CANCEL neprijatého vstupu)
        self._pending: tuple[str, int] | None = None
        #: `bar_index` baru signálu otvoreného obchodu — z neho sa počíta `maxBars`
        self._entry_idx: int | None = None

    # ------------------------------------------------------------------ #
    # swingy
    # ------------------------------------------------------------------ #

    def _is_swing_high(self, left: int, right: int) -> bool:
        """Pine `f_swingHigh` — prísne `>` na oboch stranách, kandidát je `history[right]`."""
        level = self.history[right].high
        for i in range(1, left + 1):
            if self.history[right + i].high >= level:
                return False
        for i in range(1, right + 1):
            if self.history[right - i].high >= level:
                return False
        return True

    def _is_swing_low(self, left: int, right: int) -> bool:
        level = self.history[right].low
        for i in range(1, left + 1):
            if self.history[right + i].low <= level:
                return False
        for i in range(1, right + 1):
            if self.history[right - i].low <= level:
                return False
        return True

    def _confirm_swings(self, out: EngineOutput, atr: float) -> None:
        """Swingy, ktoré sa **na tomto bare** potvrdili. Skôr o nich engine nevie.

        Poradie (najprv high, potom low) je zámerne rovnaké ako v Pine: bar, ktorý je
        zároveň swing high aj swing low (outside bar medzi inside barmi), je možný
        a bez pevného poradia by filter šumu dal raz tak a raz inak.
        """
        left, right = int(self.cfg.swingLeft), int(self.cfg.swingRight)
        if not self.history.has(left + right):
            return
        candidate = self.history[right]
        if self._is_swing_high(left, right):
            self._accept_swing(out, True, candidate.high, candidate.time, atr)
        if self._is_swing_low(left, right):
            self._accept_swing(out, False, candidate.low, candidate.time, atr)

    def _accept_swing(self, out: EngineOutput, is_high: bool, level: float, ts: int, atr: float) -> None:
        """Prijme potvrdený swing, ak nie je pod prahom šumu (`minSwingSize`).

        Veľkosť swingu je jeho vzdialenosť od **posledného prijatého swingu**, nech už bol
        ktorého druhu — teda dĺžka nohy, ktorú práve dokončil. Prvý swing behu referenciu
        nemá, takže sa prijme vždy.

        Referencia je zámerne jedna a spoločná pre obe strany. Keby sa swing high meral
        len proti poslednému swing **low**, v úzkom rozsahu by sa žiadne low neprijalo,
        referencia by ostala prázdna a všetky high by prešli — stratégia by v šume
        obchodovala len jednu stranu. To nie je filter, to je asymetria.

        Menšia noha sa ignoruje celá: úroveň sa neposunie a swing sa ani nenakreslí, aby
        bolo na grafe vidieť presne to, čo engine naozaj vidí.
        """
        min_leg = self.cfg.minSwingSize.resolve(self.inst, price=level, atr=atr)
        if self._last_swing is not None and min_leg > 0 and abs(level - self._last_swing) < min_leg:
            return
        self._last_swing = level

        if is_high:
            self._sw_high, self._sw_high_ts, self._sw_high_used = level, ts, False
        else:
            self._sw_low, self._sw_low_ts, self._sw_low_used = level, ts, False
        if not self.cfg.showStructure:
            return
        kind = ST_SWING_HIGH if is_high else ST_SWING_LOW
        out.drawings.append(DrawLabel(
            kind, ts, level, "H" if is_high else "L", _SWING_COLOR,
            style=LabelStyle.DOWN if is_high else LabelStyle.UP, above=is_high,
            obj_id=f"stsw.{ts}.{'h' if is_high else 'l'}",
        ))
        out.drawings.append(DrawLine(
            ST_LEVEL, ts, level, ts + _LEVEL_BARS * self.step_ms, level, _LEVEL_COLOR,
            style=LineStyle.DOTTED, obj_id=self._level_id(is_high, ts),
            text="Swing high" if is_high else "Swing low",
        ))

    @staticmethod
    def _level_id(is_high: bool, ts: int) -> str:
        return f"stlv.{ts}.{'h' if is_high else 'l'}"

    # ------------------------------------------------------------------ #
    # udalosti štruktúry
    # ------------------------------------------------------------------ #

    def _event(self, bar: Bar, out: EngineOutput) -> tuple[int, bool] | None:
        """(smer +1/-1, je to CHoCH?) alebo `None`. Rozhoduje **zatvorenie** baru.

        Prerazená úroveň sa spotrebuje (`_used`), takže ďalšia udalosť tým smerom
        potrebuje nový potvrdený swing — inak by BOS „nastával" na každom ďalšom bare.
        """
        up = self._sw_high is not None and not self._sw_high_used and bar.close > self._sw_high
        down = self._sw_low is not None and not self._sw_low_used and bar.close < self._sw_low
        # Obe naraz (swing low leží nad swing high) je zriedkavé, ale musí to byť
        # jednoznačné: vyhráva pokračovanie stavu, v neutrále smer tela baru.
        ev_up = up and (not down or self.state == 1 or (self.state == 0 and bar.close >= bar.open))
        ev_down = down and not ev_up
        if not (ev_up or ev_down):
            return None

        is_bos = (ev_up and self.state >= 0) or (ev_down and self.state <= 0)
        broken_ts = self._sw_high_ts if ev_up else self._sw_low_ts
        if ev_up:
            self._sw_high_used = True
        else:
            self._sw_low_used = True
        self.state = 1 if ev_up else -1

        if self.cfg.showStructure:
            # Úroveň končí presne tam, kde ju bar zavretím prerazil — Pine `line.set_x2`.
            out.drawings.append(DrawUpdate(self._level_id(ev_up, broken_ts), "x2_ms", bar.time))
            out.drawings.append(DrawLabel(
                ST_BOS if is_bos else ST_CHOCH, bar.time, bar.high if ev_up else bar.low,
                "BOS" if is_bos else "CHoCH", "#ffffff",
                style=LabelStyle.DOWN if ev_up else LabelStyle.UP, above=ev_up,
                bg_color=_BOS_COLOR if is_bos else _CHOCH_COLOR,
                obj_id=f"stev.{bar.time}",
            ))
        return (1 if ev_up else -1), not is_bos

    # ------------------------------------------------------------------ #
    # obchod
    # ------------------------------------------------------------------ #

    def _in_session(self, ts_ms: int) -> bool:
        """Obchodné okno — hodina v zvolenom pásme, aby okno nepodliezlo letný čas."""
        if not self.cfg.useSession or self._tz is None:
            return True
        hour = datetime.fromtimestamp(ts_ms / 1000, tz=self._tz).hour
        start, end = int(self.cfg.sessionStartH), int(self.cfg.sessionEndH)
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end  # okno cez polnoc

    def _stop_price(self, direction: Direction, bar: Bar, atr: float) -> float:
        """SL: za posledným potvrdeným swingom v protismere, alebo z ATR.

        Dve veci, ktoré tu musia byť a nie sú samozrejmé:

        1. Keď potvrdený swing v protismere ešte nie je, platí ATR aj v režime `swing` —
           inak by prvé obchody behu nemali stop odkiaľ vziať.
        2. Pri `sweep` vstupe je swing v protismere už prekonaný (práve preto sa vstupuje),
           takže stop musí ísť za **extrém signálneho baru**, nie za swing. Bez toho by
           stop long obchodu ležal nad vstupom a plán by bol nezmysel.
        """
        entry, long = bar.close, direction is Direction.LONG
        swing = self._sw_low if long else self._sw_high
        atr_dist = float(self.cfg.slAtrMult) * atr
        if self.cfg.slMode is SlMode.SWING and swing is not None:
            buffer = self.cfg.slBuffer.resolve(self.inst, price=entry, atr=atr)
            base = min(swing, bar.low) if long else max(swing, bar.high)
            stop = base - buffer if long else base + buffer
        else:
            stop = entry - atr_dist if long else entry + atr_dist
        if (stop >= entry) if long else (stop <= entry):
            stop = entry - atr_dist if long else entry + atr_dist
        return stop

    def _plan(self, direction: Direction, bar: Bar, atr: float) -> TradePlan | None:
        entry = bar.close
        stop = self.inst.round_price(self._stop_price(direction, bar, atr))
        long = direction is Direction.LONG
        sl_distance = (entry - stop) if long else (stop - entry)
        if sl_distance <= 0:
            return None
        reward = self.cfg.rrRatio if self.cfg.exitMode is ExitMode.RR else _TP_BACKSTOP_R
        take = entry + sl_distance * reward if long else entry - sl_distance * reward
        qty = self.inst.qty_for_risk(self.cfg.riskDollar, sl_distance) if self.cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(
            direction=direction,
            entry=entry,
            stop_loss=stop,
            take_profit=self.inst.round_price(take),
            qty=qty,
            sl_distance=sl_distance,
        )

    def _trade_drawings(self, bar: Bar, plan: TradePlan) -> list[DrawCommand]:
        """Štítok vstupu a boxy s **plánom** obchodu.

        Boxy nie sú ozdoba: `trades.json` má len to, čo Freqtrade nakoniec urobil, takže
        kresba je jediné miesto, kde ostane vzdialenosť stopu a plánovaný RR tak, ako ich
        engine vypočítal (`SPEC.sl_kind` / `tp_kind`, `tester/analytics.py`). Páruje sa to
        časom baru signálu, preto `x1_ms` musí byť `bar.time` — ten je aj v `enter_tag`.

        V režime `exitMode = structure` sa TP box **nekreslí**: obchod pevný cieľ nemá
        a nakreslený backstop na 50 R by analytike nahlásil plánovaný RR, ktorý neexistuje.
        """
        long = plan.direction is Direction.LONG
        right = bar.time + _BOX_BARS * self.step_ms
        out: list[DrawCommand] = [DrawLabel(
            ST_ENTRY, bar.time, bar.low if long else bar.high, "LONG" if long else "SHORT",
            "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"stentry.{bar.time}",
        )]
        levels = [(DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR)]
        if self.cfg.exitMode is ExitMode.RR:
            levels.insert(0, (DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR))
        for kind, price, color in levels:
            out.append(DrawBox(
                kind=kind, x1_ms=bar.time, y1=max(plan.entry, price), x2_ms=right,
                y2=min(plan.entry, price), border_color=color, fill_color=color + "40",
                border_width=0, obj_id=f"struct{bar.time}.{kind.value}",
            ))
        return out

    def _signal_direction(self, event: tuple[int, bool]) -> Direction | None:
        """Ktorý variant vstupu berie ktorú udalosť — Pine `longSig` / `shortSig`."""
        way, is_choch = event
        mode = self.cfg.entryMode
        if mode is EntryMode.BOS:
            take = not is_choch
            side = way
        elif mode is EntryMode.CHOCH:
            take = is_choch
            side = way
        else:  # SWEEP — proti CHoCH: CHoCH nadol znamená long
            take = is_choch
            side = -way
        if not take:
            return None
        direction = Direction.LONG if side > 0 else Direction.SHORT
        return direction if self.cfg.tradeDirection.allows(direction) else None

    def _close_all(self, out: EngineOutput, ctx: MarketContext, idx: int, reason: str) -> None:
        out.close_session = True
        for order_id in ctx.open_order_ids:
            out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason=reason))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        if self.cfg.useSession and self._in_session(bar.time):
            out.drawings.append(DrawBg(
                kind=DrawKind.SESSION, x1_ms=bar.time, x2_ms=bar.time + self.step_ms,
                color=with_alpha(Palette.SESSION1.value, 92), obj_id=f"stbg.{bar.time}",
                text="Obchodné okno",
            ))

        # Obchod, ktorý sa nikdy neotvoril (adaptér vstup neprijal), prestáva platiť —
        # vstup má byť na cene udalosti, nie o pol hodiny neskôr.
        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 1:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="vstup neprijatý"))
            self._pending = None
        if ctx.position_size != 0.0:
            self._pending = None  # vyplnené — sledovanie preberá adaptér
        elif self._entry_idx is not None and idx > self._entry_idx + 1:
            self._entry_idx = None  # obchod skončil (alebo nikdy nezačal)

        self._confirm_swings(out, atr)
        event = self._event(bar, out)

        # -- výstupy, ktoré engine nevie odovzdať ako order: štruktúra a čas ---------- #
        if ctx.position_size != 0.0:
            way = 1 if ctx.position_size > 0 else -1
            structure_out = (self.cfg.exitMode is ExitMode.STRUCTURE
                             and event is not None and event[0] == way)
            held = idx - self._entry_idx if self._entry_idx is not None else 0
            time_out = int(self.cfg.maxBars) > 0 and held >= int(self.cfg.maxBars)
            if structure_out:
                self._close_all(out, ctx, idx, "štruktúrna udalosť v smere obchodu")
            elif time_out:
                self._close_all(out, ctx, idx, f"časový limit {int(self.cfg.maxBars)} barov")

        # -- vstup -------------------------------------------------------------------- #
        if (event is not None and ctx.position_size == 0.0 and self._pending is None
                and atr > 0 and self._in_session(bar.time)):
            direction = self._signal_direction(event)
            plan = self._plan(direction, bar, atr) if direction is not None else None
            if plan is not None:
                order_id = f"struct:{idx}"
                reason = ("CHoCH" if event[1] else "BOS") + f" {'nahor' if event[0] > 0 else 'nadol'}"
                out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction,
                                              plan=plan, order_type=OrderType.MARKET, reason=reason))
                self._pending = (order_id, idx)
                self._entry_idx = idx
                out.drawings += self._trade_drawings(bar, plan)

        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
