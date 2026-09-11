"""Engine divergenčnej stratégie: divergencie na grafe + supertrend na dvoch vyšších TF
+ divergenčné zóny na vyšších TF → vstup s potvrdením, SL z ATR, trailing, výstup trendom.

Logika je port `DivergenceStrategy` (Freqtrade) do jedného bar-by-bar enginu, ktorý beží
rovnako vo Freqtrade, MultiCharts aj emulátore. Čo sa na ceste zmenilo, je v
`docs/PORT.md`; tu je len to, čo sa deje na každom bare:

1. Bar grafu → Heikin Ashi → detektor divergencií (indikátory podľa configu), supertrend
   grafu, RSI. Skutočný bar ide do `BarHistory` kvôli ATR pre stop.
2. Bar grafu sa skladá do dvoch vyšších TF (`TFAggregator`). Uzavretý HTF bar → jeho
   Heikin Ashi → supertrend HTF; na oboch HTF beží ešte druhý detektor divergencií
   (všetky indikátory, druh podľa `zoneSearchDiv`, bez potvrdenia) a súčet jeho zásahov za
   posledných N HTF barov je **zóna**: kým je v okne čo i len jedna medvedia divergencia,
   long sa neotvorí.
3. Signál long: býčia divergencia na niektorom z posledných `signalBars` barov (aspoň
   `minDivsLong` dvojíc) a žiadna medvedia; RSI ≤ `rsiLongMax`; supertrend oboch vyšších
   TF hore; supertrend grafu dole (pullback); žiadna medvedia zóna. Short zrkadlovo.
4. Vstup: `confirm` = signál vyzbrojí a kým trvá, vstúpi sa na prvom bare, ktorý zavrie
   nad zatváracou cenou predchádzajúceho (pôvodný trailing buy); `immediate` = hneď.
5. Výstupy: SL z ATR (veľkosť pozície z rizika), voliteľný TP (RR), dvojstupňový trailing
   (zámok + sledovanie), výstup podľa trendu pre stratový obchod, časový limit.

Engine je čistý: žiadne I/O, všetok stav v `self`. Pozíciu mu hovorí adaptér cez
`MarketContext`; sám si drží len plán obchodu, ktorý vydal, aby vedel, na ktorej strane
vstupu close leží.
"""

from __future__ import annotations

from collections import deque

from tradebot.core.drawing import (
    DrawBg,
    DrawBox,
    DrawCommand,
    DrawKind,
    DrawLabel,
    DrawLine,
    LabelStyle,
    LineStyle,
    with_alpha,
)
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

from .config import DivSource, DivergenceConfig, EntryMode, SearchDiv
from .divergence import INDICATOR_TITLES, INDICATORS, DivHits, DivergenceDetector
from .drawing import (
    DV_ARMED,
    DV_BEAR,
    DV_BULL,
    DV_ENTRY,
    DV_LINE_BEAR,
    DV_LINE_BULL,
    DV_ST_DOWN,
    DV_ST_HTF,
    DV_ST_UP,
    DV_ZONE_BEAR,
    DV_ZONE_BULL,
)
from .htf import TFAggregator
from .ta import RSI, HeikinAshi, Supertrend
from .trailing import TwoStageTrailing

__all__ = ["DivergenceEngine", "HtfState"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_HTF_COLOR = "#6366f1"
_ARMED_COLOR = "#f59e0b"

#: Ako ďaleko dopredu siaha TP/SL box — len čitateľnosť grafu.
_BOX_BARS = 30
#: TP order v režime bez pevného cieľa (`rrRatio = 0`): poistka, nie cieľ (MultiCharts
#: order vyžaduje). Box sa nekreslí, aby analytika nehlásila plánovaný RR, ktorý neexistuje.
_TP_BACKSTOP_R = 50.0
#: Zónové divergencie sa hľadajú všetkými indikátormi okrem histogramu — ako v origináli.
_ZONE_INDICATORS = frozenset(k for k in INDICATORS if k != "macdh")


class HtfState:
    """Jeden vyšší TF: skladanie, Heikin Ashi, supertrend, zónový detektor a okno súčtov."""

    __slots__ = ("agg", "ha", "st", "det", "window", "bull", "bear", "bars")

    def __init__(self, minutes: int, st_len: int, st_mult: float, det: DivergenceDetector | None,
                 window: int) -> None:
        self.agg = TFAggregator(minutes)
        self.ha = HeikinAshi()
        self.st = Supertrend(st_len, st_mult)
        self.det = det
        self.window: deque[tuple[int, int]] = deque(maxlen=max(1, int(window)))
        self.bull = 0
        self.bear = 0
        self.bars = 0

    def push(self, bar: Bar) -> Bar | None:
        """Bar grafu → ak sa ním uzavrel HTF bar, spracuje ho a vráti."""
        closed = self.agg.push(bar)
        if closed is None:
            return None
        self.bars += 1
        ha = self.ha.push(closed)
        self.st.push(ha)
        if self.det is not None:
            hits = self.det.on_bar(ha)
            self.window.append((hits.buy_count, hits.sell_count))
            self.bull = sum(b for b, _ in self.window)
            self.bear = sum(s for _, s in self.window)
        return closed

    @property
    def trend(self) -> int | None:
        return self.st.trend

    @property
    def line(self) -> float | None:
        return self.st.line


class DivergenceEngine:
    """Bar-by-bar engine. Volaj `on_bar` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: DivergenceConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = int(chart_tf_minutes)
        self.step_ms = self.chart_tf_minutes * 60_000
        for minutes in (cfg.htfMinutes, cfg.htf2Minutes):
            if int(minutes) % self.chart_tf_minutes != 0:
                raise ValueError(
                    f"vyšší TF {int(minutes)}m nie je násobkom TF grafu {self.chart_tf_minutes}m — "
                    "skladá sa z barov grafu, takže musí byť"
                )

        self.history = BarHistory(maxlen=int(cfg.atrLen) + 16, atr_len=int(cfg.atrLen))
        self.ha = HeikinAshi()
        regular = cfg.searchDiv in (SearchDiv.REGULAR, SearchDiv.BOTH)
        hidden = cfg.searchDiv in (SearchDiv.HIDDEN, SearchDiv.BOTH)
        self.detector = DivergenceDetector(
            prd=cfg.prd, source_close=cfg.source is DivSource.CLOSE, regular=regular, hidden=hidden,
            max_pp=cfg.maxPp, max_bars=cfg.maxBars, dont_confirm=cfg.dontConfirm,
            buy_inds=cfg.long_indicators, sell_inds=cfg.short_indicators,
        )
        self.st_chart = Supertrend(cfg.stLen, cfg.stMult)
        self.rsi = RSI(cfg.rsiLen)
        self.rsi_value: float | None = None
        #: posledných `signalBars` výsledkov detektora (najnovší posledný)
        self.recent: deque[DivHits] = deque(maxlen=max(1, int(cfg.signalBars)))

        def zone_det(prd: int) -> DivergenceDetector | None:
            if not cfg.zoneFilter:
                return None
            return DivergenceDetector(
                prd=prd, source_close=True,
                regular=cfg.zoneSearchDiv in (SearchDiv.REGULAR, SearchDiv.BOTH),
                hidden=cfg.zoneSearchDiv in (SearchDiv.HIDDEN, SearchDiv.BOTH), max_pp=cfg.zoneMaxPp,
                max_bars=cfg.zoneMaxBars, dont_confirm=True,
                buy_inds=_ZONE_INDICATORS, sell_inds=_ZONE_INDICATORS,
            )

        self.htf1 = HtfState(cfg.htfMinutes, cfg.stLen, cfg.stMultHtf, zone_det(cfg.zonePrd1), cfg.zoneWindow1)
        self.htf2 = HtfState(cfg.htf2Minutes, cfg.stLen, cfg.stMultHtf, zone_det(cfg.zonePrd2), cfg.zoneWindow2)

        #: koľko barov grafu treba, kým sú signály platné: divergencie potrebujú pivoty do
        #: `maxBars` dozadu, druhý vyšší TF supertrend a jeho zóny svoje bary × pomer TF
        ratio2 = int(cfg.htf2Minutes) // self.chart_tf_minutes
        chart_need = int(cfg.maxBars) + int(cfg.prd) + 40
        htf_need = (int(cfg.stLen) + 40) * ratio2
        if cfg.zoneFilter:
            htf_need = max(htf_need, (int(cfg.zoneMaxBars) + int(cfg.zonePrd2) + 10) * ratio2)
        self.required_history = max(chart_need, htf_need)

        #: vyzbrojený vstup: (smer, referenčná cena = close predchádzajúceho baru, čas baru signálu)
        self._armed: tuple[Direction, float, int] | None = None
        #: posledný vstupný order a bar, na ktorom vznikol (na CANCEL neprijatého vstupu)
        self._pending: tuple[str, int] | None = None
        #: plán obchodu, ktorý engine vydal — aby vedel, kde je vstup, kým pozícia žije
        self._open_plan: TradePlan | None = None
        self._entry_idx: int | None = None
        self.signals = 0

    # ------------------------------------------------------------------ #
    # indikátory a kresby stavu
    # ------------------------------------------------------------------ #

    def _update(self, bar: Bar, out: EngineOutput) -> DivHits:
        """Všetky indikátory na tomto bare + kresby, ktoré nesúvisia s obchodom."""
        self.history.append(bar)
        ha = self.ha.push(bar)
        hits = self.detector.on_bar(ha)
        self.recent.append(hits)
        self.st_chart.push(ha)
        self.rsi_value = self.rsi.push(ha.close)
        self.htf1.push(bar)
        self.htf2.push(bar)

        cfg = self.cfg
        if cfg.showDivergences:
            self._draw_divergences(bar, hits, out)
        if cfg.showSupertrend:
            self._draw_supertrend(bar, out)
        if cfg.showZones and cfg.zoneFilter:
            self._draw_zones(bar, out)
        return hits

    def _draw_divergences(self, bar: Bar, hits: DivHits, out: EngineOutput) -> None:
        for bullish, side in ((True, hits.buy), (False, hits.sell)):
            if not side:
                continue
            price = bar.low if bullish else bar.high
            for hit in side:
                out.drawings.append(DrawLine(
                    DV_LINE_BULL if bullish else DV_LINE_BEAR, hit.pivot_time, hit.pivot_price,
                    bar.time, price, _LONG_COLOR if bullish else _SHORT_COLOR,
                    style=LineStyle.DASHED if hit.hidden else LineStyle.SOLID,
                    obj_id=f"dvln.{bar.time}.{hit.indicator}.{'h' if hit.hidden else 'r'}.{'b' if bullish else 's'}",
                    text=f"{INDICATOR_TITLES.get(hit.indicator, hit.indicator)} "
                         f"{'skrytá' if hit.hidden else 'regulárna'} {'býčia' if bullish else 'medvedia'}",
                ))
            names = " ".join(dict.fromkeys(INDICATOR_TITLES.get(h.indicator, h.indicator) for h in side))
            out.drawings.append(DrawLabel(
                DV_BULL if bullish else DV_BEAR, bar.time, price, names,
                _LONG_COLOR if bullish else _SHORT_COLOR,
                style=LabelStyle.UP if bullish else LabelStyle.DOWN, above=not bullish,
                obj_id=f"dvlb.{bar.time}.{'b' if bullish else 's'}",
            ))

    def _draw_supertrend(self, bar: Bar, out: EngineOutput) -> None:
        st = self.st_chart
        if st.line is not None and st.trend is not None:
            up = st.trend == 1
            out.drawings.append(DrawLine(
                DV_ST_UP if up else DV_ST_DOWN, bar.time, st.line, bar.time + self.step_ms, st.line,
                _LONG_COLOR if up else _SHORT_COLOR, width=2, obj_id=f"dvst.{bar.time}",
                text=f"Supertrend {self.chart_tf_minutes}m {'hore' if up else 'dole'}",
            ))
        line2 = self.htf2.line
        if line2 is not None:
            out.drawings.append(DrawLine(
                DV_ST_HTF, bar.time, line2, bar.time + self.step_ms, line2, _HTF_COLOR,
                style=LineStyle.DOTTED, obj_id=f"dvsth.{bar.time}",
                text=f"Supertrend {int(self.cfg.htf2Minutes)}m {'hore' if self.htf2.trend == 1 else 'dole'}",
            ))

    def _draw_zones(self, bar: Bar, out: EngineOutput) -> None:
        bear = self.htf1.bear > 0 or self.htf2.bear > 0
        bull = self.htf1.bull > 0 or self.htf2.bull > 0
        if bear:
            out.drawings.append(DrawBg(
                kind=DV_ZONE_BEAR, x1_ms=bar.time, x2_ms=bar.time + self.step_ms,
                color=with_alpha(_SHORT_COLOR, 92), obj_id=f"dvzb.{bar.time}",
                text="Medvedia divergenčná zóna (blokuje long)",
            ))
        if bull:
            out.drawings.append(DrawBg(
                kind=DV_ZONE_BULL, x1_ms=bar.time, x2_ms=bar.time + self.step_ms,
                color=with_alpha(_LONG_COLOR, 92), obj_id=f"dvzu.{bar.time}",
                text="Býčia divergenčná zóna (blokuje short)",
            ))

    # ------------------------------------------------------------------ #
    # signál
    # ------------------------------------------------------------------ #

    def _signal(self) -> Direction | None:
        """Long / short / nič — všetky filtre pôvodného `populate_entry_trend`."""
        cfg = self.cfg
        if self.rsi_value is None or self.htf1.trend is None or self.htf2.trend is None:
            return None
        if cfg.pullbackFilter and self.st_chart.trend is None:
            return None
        recent = list(self.recent)
        if len(recent) < self.recent.maxlen:
            return None
        long_div = (any(h.buy_count >= int(cfg.minDivsLong) for h in recent)
                    and all(h.sell_count == 0 for h in recent))
        short_div = (any(h.sell_count >= int(cfg.minDivsShort) for h in recent)
                     and all(h.buy_count == 0 for h in recent))

        if long_div and cfg.tradeDirection.allows(Direction.LONG):
            ok = (self.rsi_value <= float(cfg.rsiLongMax)
                  and self.htf1.trend == 1 and self.htf2.trend == 1
                  and (not cfg.pullbackFilter or self.st_chart.trend == -1)
                  and (not cfg.zoneFilter or (self.htf1.bear == 0 and self.htf2.bear == 0)))
            if ok:
                return Direction.LONG
        if short_div and cfg.tradeDirection.allows(Direction.SHORT):
            ok = (self.rsi_value >= float(cfg.rsiShortMin)
                  and self.htf1.trend == -1 and self.htf2.trend == -1
                  and (not cfg.pullbackFilter or self.st_chart.trend == 1)
                  and (not cfg.zoneFilter or (self.htf1.bull == 0 and self.htf2.bull == 0)))
            if ok:
                return Direction.SHORT
        return None

    # ------------------------------------------------------------------ #
    # obchod
    # ------------------------------------------------------------------ #

    def _plan(self, direction: Direction, bar: Bar, atr: float) -> TradePlan | None:
        cfg = self.cfg
        entry = bar.close
        sl_distance = float(cfg.slAtrMult) * atr
        if sl_distance <= 0:
            return None
        long = direction is Direction.LONG
        stop = self.inst.round_price(entry - sl_distance if long else entry + sl_distance)
        sl_distance = (entry - stop) if long else (stop - entry)
        if sl_distance <= 0:
            return None
        reward = float(cfg.rrRatio) if cfg.rrRatio > 0 else _TP_BACKSTOP_R
        take = entry + sl_distance * reward if long else entry - sl_distance * reward
        qty = self.inst.qty_for_risk(cfg.riskDollar, sl_distance) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(
            direction=direction,
            entry=entry,
            stop_loss=stop,
            take_profit=self.inst.round_price(take),
            qty=qty,
            sl_distance=sl_distance,
            trailing=TwoStageTrailing.from_config(cfg, self.inst, entry),
        )

    def _trade_drawings(self, bar: Bar, plan: TradePlan, signal_ts: int) -> list[DrawCommand]:
        """Štítok vstupu a boxy s plánom. `x1_ms` boxov je čas baru VSTUPU (ten je v `enter_tag`)."""
        long = plan.direction is Direction.LONG
        right = bar.time + _BOX_BARS * self.step_ms
        out: list[DrawCommand] = [DrawLabel(
            DV_ENTRY, bar.time, bar.low if long else bar.high, "LONG" if long else "SHORT",
            "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"dventry.{bar.time}",
        )]
        levels = [(DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR)]
        if self.cfg.rrRatio > 0:
            levels.insert(0, (DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR))
        for kind, price, color in levels:
            out.append(DrawBox(
                kind=kind, x1_ms=bar.time, y1=max(plan.entry, price), x2_ms=right,
                y2=min(plan.entry, price), border_color=color, fill_color=color + "40",
                border_width=0, obj_id=f"div{bar.time}.{kind.value}",
                text=f"signál {signal_ts}",
            ))
        return out

    def _close_all(self, out: EngineOutput, ctx: MarketContext, idx: int, reason: str) -> None:
        out.close_session = True
        for order_id in ctx.open_order_ids:
            out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason=reason))

    def _enter(self, direction: Direction, bar: Bar, out: EngineOutput, idx: int, signal_ts: int,
               reason: str) -> bool:
        atr = self.history.atr
        if atr <= 0:
            return False
        plan = self._plan(direction, bar, atr)
        if plan is None:
            return False
        order_id = f"div:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction, plan=plan,
                                      order_type=OrderType.MARKET, reason=reason))
        self._pending = (order_id, idx)
        self._open_plan = plan
        self._entry_idx = idx
        self.signals += 1
        out.drawings += self._trade_drawings(bar, plan, signal_ts)
        return True

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        self._update(bar, out)
        idx = self.history.bar_index
        cfg = self.cfg

        # Vstup, ktorý adaptér neprijal, prestáva platiť — nemá sa plniť o bar neskôr.
        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 1:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="vstup neprijatý"))
            self._pending = None
            self._open_plan = None
            self._entry_idx = None
        if ctx.position_size != 0.0:
            self._pending = None  # vyplnené — sledovanie preberá adaptér
        elif self._entry_idx is not None and idx > self._entry_idx + 1:
            self._open_plan = None  # obchod skončil (SL/TP/trailing u adaptéra)
            self._entry_idx = None

        # -- výstupy, ktoré nejdú ako order: trend a čas --------------------------------- #
        if ctx.position_size != 0.0 and self._open_plan is not None:
            plan = self._open_plan
            long = plan.direction is Direction.LONG
            losing = bar.close <= plan.entry if long else bar.close >= plan.entry
            t2, line2 = self.htf2.trend, self.htf2.line
            trend_break = t2 is not None and line2 is not None and (
                (t2 == -1 or bar.close < line2) if long else (t2 == 1 or bar.close > line2)
            )
            held = idx - self._entry_idx if self._entry_idx is not None else 0
            if cfg.trendExit and losing and trend_break:
                self._close_all(out, ctx, idx, f"supertrend {int(cfg.htf2Minutes)}m proti obchodu")
            elif int(cfg.maxHoldBars) > 0 and held >= int(cfg.maxHoldBars):
                self._close_all(out, ctx, idx, f"časový limit {int(cfg.maxHoldBars)} barov")

        # -- vstup ------------------------------------------------------------------------ #
        signal = self._signal()
        can_enter = ctx.position_size == 0.0 and self._pending is None

        if cfg.entryMode is EntryMode.IMMEDIATE:
            self._armed = None
            if signal is not None and can_enter:
                self._enter(signal, bar, out, idx, bar.time, "divergencia")
            return out

        # confirm: pôvodný trailing buy. Kým signál trvá (divergencia žije `signalBars`
        # barov a filtre držia), každý bar sa porovná close s close predchádzajúceho baru;
        # prvý bar v smere obchodu vstupuje. Keď signál zmizne alebo otočí, čakanie končí.
        if signal is None or not can_enter:
            self._armed = None
            return out
        if self._armed is not None and self._armed[0] is not signal:
            self._armed = None
        if self._armed is not None:
            direction, ref, signal_ts = self._armed
            long = direction is Direction.LONG
            if (bar.close > ref) if long else (bar.close < ref):
                self._armed = None
                self._enter(direction, bar, out, idx, signal_ts, "divergencia, potvrdené pohybom")
                return out
            self._armed = (direction, bar.close, signal_ts)
            return out

        self._armed = (signal, bar.close, bar.time)
        if cfg.showDivergences:
            long = signal is Direction.LONG
            out.drawings.append(DrawLabel(
                DV_ARMED, bar.time, bar.low if long else bar.high, "▲" if long else "▼",
                _ARMED_COLOR, style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                obj_id=f"dvarm.{bar.time}",
            ))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
