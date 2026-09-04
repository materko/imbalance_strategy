"""Prevedie `IBSEngine` cez pandas DataFrame a výsledok zapíše do stĺpcov.

Prečo cyklom a nie vektorovo: stratégia je stavový automat na každú zónu zvlášť,
kde každý krok závisí od predchádzajúceho aj od ostatných zón (OCO, opačná
pozícia, duplicitný gap). Vektorizovať sa to nedá — viď ARCHITECTURE_port.md §1.

Runner je **inkrementálny**. Freqtrade volá `populate_indicators()` v dry/live
opakovane nad rastúcim DataFrame; prehnať engine zakaždým od nuly by bolo pomalé
a v backteste zbytočné, takže si pamätá, po ktorý bar už dobehol.

### Fill model
Engine potrebuje vedieť, či order už beží (`oppositeOpen`, OCO, STATE 5), ale
v čase výpočtu indikátorov ešte reálne fily neexistujú. Runner preto drží vlastný
jednoduchý model vyplnenia — limitka sa vyplní, keď ju bar pretne. Slúži **len na
to, aby stavový automat videl konzistentný svet**; skutočné vyplnenie rieši
Freqtrade s `--timeframe-detail 1m`. Malá odchýlka medzi tým, čo predpokladal
engine, a tým, čo Freqtrade skutočne vykonal, je očakávaná a je popísaná
v ARCHITECTURE_port.md §7.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from ...core import (
    htf_window_opens,
    Bar,
    HTFWindow,
    IBSConfig,
    IBSEngine,
    InstrumentSpec,
    MarketContext,
    OrderAction,
    OrderIntent,
)
from ...core.types import Direction

__all__ = ["SignalRow", "EngineRunner", "COLUMNS"]

#: Stĺpce, ktoré runner zapisuje do DataFrame.
COLUMNS = (
    "ibs_enter_long",
    "ibs_enter_short",
    "ibs_entry",
    "ibs_sl",
    "ibs_tp",
    "ibs_qty",
    "ibs_zone_uid",
    "ibs_in_trade_window",
)


@dataclass
class SignalRow:
    """Jeden riadok výstupu — presne to, čo sa zapíše do DataFrame."""

    enter_long: int = 0
    enter_short: int = 0
    entry: float = float("nan")
    stop_loss: float = float("nan")
    take_profit: float = float("nan")
    qty: float = float("nan")
    zone_uid: float = float("nan")
    in_trade_window: bool = False


class _PendingOrder:
    __slots__ = ("intent", "filled")

    def __init__(self, intent: OrderIntent) -> None:
        self.intent = intent
        self.filled = False


class EngineRunner:
    """Drží engine pre jeden pár a spracúva len nové bary."""

    def __init__(self, cfg: IBSConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = chart_tf_minutes
        self.engine = IBSEngine(cfg, inst, chart_tf_minutes)

        self.htf_ms = int(cfg.zoneDetectionTF) * 60_000
        self._prev_htf_open: int | None = None
        self._orders: dict[str, _PendingOrder] = {}
        self._position = 0.0

        #: čas posledného spracovaného baru — kvôli inkrementálnemu behu
        self.last_ts: int | None = None
        self.rows: dict[int, SignalRow] = {}
        #: len bary, na ktorých vznikol vstupný signál (zoradené) — na spätné dohľadanie
        self.signal_ts: list[int] = []

    # ------------------------------------------------------------------ #

    @property
    def _open_ids(self) -> frozenset[str]:
        return frozenset(k for k, o in self._orders.items() if o.filled)

    def _simulate_fills(self, bar: Bar) -> None:
        """Zámerne najjednoduchší model — viď poznámku v hlavičke modulu."""
        for order in self._orders.values():
            plan = order.intent.plan
            if plan is None:
                continue
            if not order.filled:
                if bar.low <= plan.entry <= bar.high:
                    order.filled = True
                    self._position = 1.0 if plan.direction is Direction.LONG else -1.0
                continue

            long = plan.direction is Direction.LONG
            hit_sl = bar.low <= plan.stop_loss if long else bar.high >= plan.stop_loss
            hit_tp = bar.high >= plan.take_profit if long else bar.low <= plan.take_profit
            if hit_sl or hit_tp:
                order.filled = False
                self._position = 0.0

    def _apply(self, orders: list[OrderIntent]) -> None:
        for intent in orders:
            if intent.action is OrderAction.ENTRY:
                self._orders[intent.order_id] = _PendingOrder(intent)
            elif intent.action is OrderAction.CANCEL:
                self._orders.pop(intent.order_id, None)

    # ------------------------------------------------------------------ #

    def process(self, bar: Bar, htf: HTFWindow | None) -> SignalRow:
        """Posunie engine o jeden bar a vráti riadok signálov."""
        self._simulate_fills(bar)

        ctx = MarketContext(
            in_trade_window=False,  # engine si to prepíše z vlastných hodín
            position_size=self._position,
            open_order_ids=self._open_ids,
        )
        out = self.engine.on_bar(bar, htf, ctx)
        self._apply(out.orders)
        self.last_ts = bar.time

        row = SignalRow(in_trade_window=bool(out.clock and out.clock.in_trade_window))
        for intent in out.orders:
            if intent.action is not OrderAction.ENTRY or intent.plan is None:
                continue
            plan = intent.plan
            if plan.direction is Direction.LONG:
                row.enter_long = 1
            else:
                row.enter_short = 1
            row.entry = plan.entry
            row.stop_loss = plan.stop_loss
            row.take_profit = plan.take_profit
            row.qty = plan.qty
            row.zone_uid = float(intent.zone_uid)

        self.rows[bar.time] = row
        if row.enter_long or row.enter_short:
            self.signal_ts.append(bar.time)
        return row

    def signal_at_or_before(self, ts_ms: int) -> SignalRow | None:
        """Posledný vstupný signál v čase <= `ts_ms`.

        Freqtrade otvára obchod až na sviečke PO signáli a `custom_*` callbacky
        dostávajú čas tej neskoršej sviečky, takže sa treba pozrieť dozadu. Brať
        namiesto toho posledný spracovaný bar by v backteste znamenalo koniec celého
        DataFrame - a presne na tom stratégia najprv neotvorila ani jeden obchod.
        """
        idx = bisect.bisect_right(self.signal_ts, ts_ms) - 1
        if idx < 0:
            return None
        return self.rows.get(self.signal_ts[idx])

    # ------------------------------------------------------------------ #

    def htf_window_for(self, ts_ms: int, htf_bars: dict[int, Bar], vol_sma: dict[int, float]):
        """Okno štyroch uzavretých HTF barov — ale len na bare, kde začala nová perióda.

        Presne Pine `first5mTick`: pattern sa hľadá raz za novú periódu detekčného TF
        a výhradne z už uzavretých barov, takže nič nerepaintuje.

        Ktoré štyri bary to sú, počíta `htf_window_opens()` z ČASU UZAVRETIA baru grafu —
        nie z jeho otvorenia. Pri neprekrývajúcich sa mriežkach (3m graf / 5m detekcia)
        sa tie dve odpovede líšia a rozdiel bolo vidieť ako 104 zón oproti 77 v TradingView.
        """
        htf_open = ts_ms // self.htf_ms * self.htf_ms
        is_new_period = self._prev_htf_open is not None and htf_open != self._prev_htf_open
        self._prev_htf_open = htf_open
        if not is_new_period:
            return None

        opens = htf_window_opens(ts_ms, self.chart_tf_minutes * 60_000, self.htf_ms)
        if any(o not in htf_bars for o in opens):
            return None
        return HTFWindow(tuple(htf_bars[o] for o in opens), vol_sma.get(opens[0], 0.0))
