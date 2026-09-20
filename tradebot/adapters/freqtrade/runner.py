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
jednoduchý model vyplnenia — limitka sa vyplní, keď sa obchoduje za jej cenu alebo lepšiu,
market vstup na prvom bare po zadaní (`tradebot.core.orders.entry_fills`). Slúži **len na
to, aby stavový automat videl konzistentný svet**; skutočné vyplnenie rieši
Freqtrade s `--timeframe-detail 1m`. Malá odchýlka medzi tým, čo predpokladal
engine, a tým, čo Freqtrade skutočne vykonal, je očakávaná a je popísaná
v ARCHITECTURE_port.md §7.
"""

from __future__ import annotations

import bisect
import gzip
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ...core import Bar, DrawRegistry, InstrumentSpec, MarketContext, OrderAction, OrderIntent
from ...core.orders import entry_fills
from ...core.config import StrategyConfig
from ...core.drawing import objects_to_dicts
from ...core.money import trade_money
from ...core.risk import TrailingPlan, extreme_before_stop
from ...core.types import Direction
from ...strategies import StrategySpec, spec_for_config

__all__ = ["SignalRow", "EngineRunner", "COLUMNS", "COLUMN_ATTRS", "export_chart"]

#: Stĺpec v DataFrame -> pole `SignalRow`. Prefix `tb_` je spoločný pre všetky stratégie.
COLUMN_ATTRS = {
    "tb_enter_long": "enter_long",
    "tb_enter_short": "enter_short",
    "tb_entry": "entry",
    "tb_sl": "stop_loss",
    "tb_tp": "take_profit",
    "tb_qty": "qty",
    "tb_source_id": "source_id",
    "tb_in_trade_window": "in_trade_window",
    #: engine povedal „zavri všetko" (koniec seansy) — AI nálepka na tom bare obchod
    #: uzavrie tak, ako ho uzavrie stratégia, namiesto čakania na TP/SL do nekonečna
    "tb_close_session": "close_session",
}

#: Stĺpce, ktoré runner zapisuje do DataFrame.
COLUMNS = tuple(COLUMN_ATTRS)


@dataclass
class SignalRow:
    """Jeden riadok výstupu — presne to, čo sa zapíše do DataFrame."""

    enter_long: int = 0
    enter_short: int = 0
    entry: float = float("nan")
    stop_loss: float = float("nan")
    take_profit: float = float("nan")
    qty: float = float("nan")
    #: identita zdroja signálu (IBS: uid zóny)
    source_id: float = float("nan")
    in_trade_window: bool = False
    #: Na tomto bare Pine zatvara vsetko otvorene - koniec poslednej seansy dna.
    close_session: bool = False
    #: Trailing z plánu obchodu (`TradePlan.trailing`), alebo `None`. Do DataFrame nejde
    #: (nie je v `COLUMN_ATTRS`) — číta ho `custom_stoploss` cez `signal_at`, rovnako
    #: ako MultiCharts runner berie `plan.trailing`.
    trailing: TrailingPlan | None = None


def _utc_day(ts_ms: int) -> str:
    """Pine `todayKey` — deň sa počíta v UTC bez ohľadu na časové pásma seáns."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


class _PendingOrder:
    __slots__ = ("intent", "filled", "extreme")

    def __init__(self, intent: OrderIntent) -> None:
        self.intent = intent
        self.filled = False
        #: najlepšia cena od vyplnenia (vstup trailingu); `None` = ešte žiadny bar po vyplnení
        self.extreme: float | None = None


class EngineRunner:
    """Drží engine pre jeden pár a spracúva len nové bary.

    Stratégia sa berie z registry podľa triedy configu (`spec_for_config`), takže
    `EngineRunner(cfg, inst, tf)` funguje pre každú registrovanú stratégiu.
    """

    def __init__(self, cfg: StrategyConfig, inst: InstrumentSpec, chart_tf_minutes: int,
                 spec: StrategySpec | None = None, fee: float = 0.0) -> None:
        self.spec = spec or spec_for_config(cfg)
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = chart_tf_minutes
        #: poplatok na stranu (Freqtrade `--fee`) — len na to, či bol obchod výhra (`maxDailyWins`)
        self.fee = float(fee or 0.0)
        assert self.spec.engine_factory is not None, f"{self.spec.key}: chýba engine_factory"
        self.engine = self.spec.engine_factory(cfg, inst, chart_tf_minutes)

        #: feeder informatívneho TF (IBS: okno detekčného TF zón), alebo None — engine bez HTF
        self.htf = self.spec.htf_feeder(cfg, chart_tf_minutes) if self.spec.htf_feeder else None
        self.htf_ms = getattr(self.htf, "htf_ms", None)
        self._orders: dict[str, _PendingOrder] = {}
        #: Pine `dailyWinsCount` — UTC deň -> počet obchodov zavretých v zisku.
        self._daily_wins: dict[str, int] = {}

        #: čas posledného spracovaného baru — kvôli inkrementálnemu behu
        self.last_ts: int | None = None
        self.first_ts: int | None = None
        #: Predhistória grafu v baroch (Freqtrade `startup_candle_count`): kým runner nespracoval
        #: toľko barov, signály nie sú platné. Backtest ich Freqtrade oreže sám, dry/live ich
        #: adaptér vynuluje (`ready_at`). 0 = platné od prvého baru.
        self.min_history = 0
        #: koľko barov runner spracoval
        self.processed = 0
        #: čas prvého baru, pred ktorým runner spracoval `min_history` barov
        self.ready_ts: int | None = None
        self.last_bar: Bar | None = None
        #: Finálny stav všetkého, čo engine nakreslil (Pine `box.set_*` prehraté).
        #: Webapp si to po behu uloží ku výsledku — viď `export_chart`.
        self.registry = DrawRegistry()
        self.rows: dict[int, SignalRow] = {}
        #: len bary, na ktorých vznikol vstupný signál (zoradené) — na spätné dohľadanie
        self.signal_ts: list[int] = []

    # ------------------------------------------------------------------ #

    @property
    def _open_ids(self) -> frozenset[str]:
        return frozenset(k for k, o in self._orders.items() if o.filled)

    @property
    def _position(self) -> float:
        """Pine `strategy.position_size` — odvodené z vyplnených orderov, nie držané
        ako samostatné číslo. Dva vyplnené ordery rovnakého smeru sa tak sčítajú
        a zavretie jedného z nich nezmaže aj ten druhý."""
        pos = 0.0
        for o in self._orders.values():
            if o.filled and o.intent.plan is not None:
                pos += 1.0 if o.intent.plan.direction is Direction.LONG else -1.0
        return pos

    def wins_today(self, ts_ms: int) -> int:
        return self._daily_wins.get(_utc_day(ts_ms), 0)

    @staticmethod
    def _stop_on_bar(order: _PendingOrder, bar: Bar) -> tuple[float, bool]:
        """(stop, zasiahnutý?) pre vyplnený order na tomto bare — s trailingom z plánu.

        Rovnaké pravidlo ako `TradebotStrategyBase._trailing_stop`, len na bare grafu:
        priaznivý extrém prvý → posunutý stop proti low (high); nepriaznivý prvý → starý
        stop proti low, a keď vydrží, posunutý stop proti `close` (spiatočná noha baru).
        """
        plan = order.intent.plan
        long = plan.direction is Direction.LONG
        if plan.trailing is None:
            stop = plan.stop_loss
            return stop, (bar.low <= stop if long else bar.high >= stop)

        prev = order.extreme if order.extreme is not None else plan.entry
        best = bar.high if long else bar.low
        after = max(prev, best) if long else min(prev, best)
        order.extreme = after
        before_stop = plan.trailing.stop_price(plan.direction, plan.entry, plan.stop_loss, prev)
        after_stop = plan.trailing.stop_price(plan.direction, plan.entry, plan.stop_loss, after)
        if extreme_before_stop(bar.open, bar.high, bar.low, long=long):
            return after_stop, (bar.low <= after_stop if long else bar.high >= after_stop)
        if (bar.low <= before_stop) if long else (bar.high >= before_stop):
            return before_stop, True
        return after_stop, (bar.close <= after_stop if long else bar.close >= after_stop)

    def _net_pnl(self, plan, exit_price: float) -> float:
        """Zisk uzavretého obchodu po poplatku — ako `strategy.closedtrades.profit`
        (a `_net_pnl` emulátora MultiCharts)."""
        qty = plan.qty if plan.qty == plan.qty and plan.qty > 0 else 1.0
        return trade_money(plan.entry, exit_price, qty, is_short=plan.direction is not Direction.LONG,
                           point_value=self.inst.point_value, fee_open=self.fee).net

    def _simulate_fills(self, bar: Bar) -> None:
        """Zámerne najjednoduchší model — viď poznámku v hlavičke modulu."""
        for order_id, order in list(self._orders.items()):
            plan = order.intent.plan
            if plan is None:
                continue
            if not order.filled:
                # Market vstup (IBS: Pin Bar / Engulfing) na dotyk nečaká. Do 2026-09-20 sa tu každý
                # vstup bral ako limitka „vnútri baru": market order, ktorému cena hneď ušla, ostal
                # v modeli nevyplnený, hoci ho platforma vyplnila (NinjaTrader, MNQ 2026-09-03 LONG_944).
                if entry_fills(order.intent.order_type, plan.direction, plan.entry, bar.low, bar.high):
                    order.filled = True
                continue

            long = plan.direction is Direction.LONG
            stop, hit_sl = self._stop_on_bar(order, bar)
            hit_tp = bar.high >= plan.take_profit if long else bar.low <= plan.take_profit
            if not (hit_sl or hit_tp):
                continue

            # Obchod skončil. Order z modelu MUSÍ vypadnúť: keby tu ostal ako
            # „nevyplnený", ďalší bar, ktorý pretne vstupnú cenu, by ho vyplnil
            # znova a engine by videl fantómovú pozíciu — tá blokuje opačné vstupy
            # („OPACNA POZICIA") a na konci seansy vyrobí CLOSE bez obchodu.
            del self._orders[order_id]

            # Pine `dailyWinsCount`: výhra = uzavretý obchod so ziskom > 0 po poplatku
            # (`strategy.closedtrades.profit`), teda aj trailing stop nad vstupom — rovnaká
            # definícia ako `MCRunner._daily_win_limit`. Bar, ktorý pretne stop aj TP, je bez
            # 1m detailu nerozhodnuteľný — berie sa konzervatívne stop, rovnako ako
            # v `tester.compare.scan_trades` a v emulátore MultiCharts. Obchod zavretý koncom
            # seansy (CLOSE intent) sem nepríde a nepočíta sa, ako v Pine.
            if hit_sl:
                exit_price = min(stop, bar.open) if long else max(stop, bar.open)
            else:
                exit_price = max(plan.take_profit, bar.open) if long else min(plan.take_profit, bar.open)
            if self._net_pnl(plan, exit_price) > 0:
                day = _utc_day(bar.time)
                self._daily_wins[day] = self._daily_wins.get(day, 0) + 1

    def _apply(self, orders: list[OrderIntent]) -> None:
        for intent in orders:
            if intent.action is OrderAction.ENTRY:
                self._orders[intent.order_id] = _PendingOrder(intent)
            elif intent.action in (OrderAction.CANCEL, OrderAction.CLOSE):
                self._orders.pop(intent.order_id, None)

    # ------------------------------------------------------------------ #

    def process(self, bar: Bar, htf=None) -> SignalRow:
        """Posunie engine o jeden bar a vráti riadok signálov."""
        # Pine vyhodnocuje `dailyWinLimitReached` na začiatku baru, ešte PRED tým,
        # než sa výhra z tohto baru pripočíta — limit teda platí až od ďalšieho baru.
        # Stratégia bez denného limitu (pole `maxDailyWins`) ho nemá nikdy.
        max_wins = getattr(self.cfg, "maxDailyWins", None)
        daily_limit = max_wins is not None and self.wins_today(bar.time) >= max_wins
        self._simulate_fills(bar)

        ctx = MarketContext(
            in_trade_window=False,  # engine si to prepíše z vlastných hodín
            position_size=self._position,
            daily_win_limit_reached=daily_limit,
            open_order_ids=self._open_ids,
        )
        out = self.engine.on_bar(bar, htf, ctx)
        self._apply(out.orders)
        self.registry.extend(out.drawings)
        if self.first_ts is None:
            self.first_ts = bar.time
        if self.ready_ts is None and self.processed >= self.min_history:
            self.ready_ts = bar.time
        self.processed += 1
        self.last_ts = bar.time
        self.last_bar = bar

        clock = getattr(out, "clock", None)  # stratégia bez seáns obchoduje vždy
        row = SignalRow(
            in_trade_window=bool(clock.in_trade_window) if clock is not None else True,
            close_session=out.close_session,
        )
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
            row.trailing = plan.trailing
            row.source_id = float(intent.source_id)

        self.rows[bar.time] = row
        if row.enter_long or row.enter_short:
            self.signal_ts.append(bar.time)
        return row

    def ready_at(self, ts_ms: int) -> bool:
        """Bar `ts_ms` má za sebou `min_history` barov predhistórie — signál z neho smie obchodovať."""
        return self.ready_ts is not None and ts_ms >= self.ready_ts

    def signal_at(self, ts_ms: int) -> SignalRow | None:
        """Vstupný signál presne na bare `ts_ms`, alebo `None`.

        Toto je primárna cesta: stratégia si čas baru signálu nesie v `enter_tag`
        obchodu, takže SL, TP aj veľkosť sa berú vždy z toho signálu, z ktorého
        obchod naozaj vznikol. `signal_at_or_before` je len záloha.
        """
        row = self.rows.get(ts_ms)
        if row is None or not (row.enter_long or row.enter_short):
            return None
        return row

    def signal_at_or_before(self, ts_ms: int) -> SignalRow | None:
        """Posledný vstupný signál v čase <= `ts_ms`.

        Freqtrade otvára obchod až na sviečke PO signáli a `custom_*` callbacky
        dostávajú čas tej neskoršej sviečky, takže sa treba pozrieť dozadu. Brať
        namiesto toho posledný spracovaný bar by v backteste znamenalo koniec celého
        DataFrame - a presne na tom stratégia najprv neotvorila ani jeden obchod.

        Pozor: keď engine vygeneruje signál aj na sviečke, na ktorej Freqtrade
        obchod otvára (iná zóna o bar neskôr), `<=` vráti ten novší a obchod by
        dostal cudzí SL/TP. Preto je to len záloha pre obchody bez `enter_tag`
        (napr. force entry) — bežná cesta ide cez `signal_at`.
        """
        idx = bisect.bisect_right(self.signal_ts, ts_ms) - 1
        if idx < 0:
            return None
        return self.rows.get(self.signal_ts[idx])

    # ------------------------------------------------------------------ #

    def window_for(self, ts_ms: int):
        """Čo dostane engine ako `htf` na tomto bare — z feedera stratégie, inak `None`."""
        return self.htf.window_for(ts_ms) if self.htf is not None else None

    def htf_window_for(self, ts_ms: int, htf_bars: dict[int, Bar], vol_sma: dict[int, float]):
        """IBS: okno štyroch uzavretých HTF barov na bare, kde začala nová perióda — viď `HTFFeeder`.

        `htf_bars`/`vol_sma` sú predpočítané z informative dataframe; podávajú sa
        referenciou, takže opakované volanie na každom bare nič nekopíruje.
        """
        if self.htf is None:
            return None
        self.htf.load(htf_bars, vol_sma)
        return self.htf.window_for(ts_ms)


# --------------------------------------------------------------------------- #
# Export kresieb pre webapp
# --------------------------------------------------------------------------- #


def export_chart(runner: EngineRunner, pair: str, timeframe: str, path: Path | str) -> dict:
    """Zapíše finálny stav kresieb behu do JSON (gzip, ak cesta končí `.gz`).

    Pridá aj to, čo stratégia kreslí až na poslednom bare (`final_drawings`, IBS: S/R
    zhluky a Elliott). Vracia hlavičku súboru (bez objektov) — na log.
    """
    objects = list(runner.registry.objects())
    if runner.last_bar is not None:
        objects.extend(runner.engine.final_drawings(runner.last_bar))
    dicts = objects_to_dicts(objects)
    counts: dict[str, int] = {}
    for d in dicts:
        counts[d["k"]] = counts.get(d["k"], 0) + 1
    data = {
        "version": 1,
        "strategy": runner.spec.key,
        "pair": pair,
        "timeframe": timeframe,
        "from_ms": runner.first_ts,
        "to_ms": runner.last_ts,
        "bars": len(runner.rows),
        "counts": counts,
        "objects": dicts,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if path.suffix == ".gz":
        with gzip.open(path, "wb", compresslevel=6) as fh:
            fh.write(raw)
    else:
        path.write_bytes(raw)
    return {k: v for k, v in data.items() if k != "objects"}
