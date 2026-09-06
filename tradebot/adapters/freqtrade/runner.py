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
import gzip
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ...strategies.ibs.htf import HTFFeeder
from ...core import (
    htf_window_opens,
    Bar,
    DrawRegistry,
    HTFWindow,
    IBSConfig,
    IBSEngine,
    InstrumentSpec,
    MarketContext,
    OrderAction,
    OrderIntent,
)
from ...core.drawing import objects_to_dicts
from ...core.types import Direction

__all__ = ["SignalRow", "EngineRunner", "COLUMNS", "export_chart"]

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
    #: Na tomto bare Pine zatvara vsetko otvorene - koniec poslednej seansy dna.
    close_session: bool = False


def _utc_day(ts_ms: int) -> str:
    """Pine `todayKey` — deň sa počíta v UTC bez ohľadu na časové pásma seáns."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


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

        #: okno detekčného TF — jedna implementácia pre Freqtrade aj MultiCharts
        self.htf = HTFFeeder(cfg, chart_tf_minutes)
        self.htf_ms = self.htf.htf_ms
        self._orders: dict[str, _PendingOrder] = {}
        #: Pine `dailyWinsCount` — UTC deň -> počet obchodov zavretých v zisku.
        self._daily_wins: dict[str, int] = {}

        #: čas posledného spracovaného baru — kvôli inkrementálnemu behu
        self.last_ts: int | None = None
        self.first_ts: int | None = None
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

    def _simulate_fills(self, bar: Bar) -> None:
        """Zámerne najjednoduchší model — viď poznámku v hlavičke modulu."""
        for order_id, order in list(self._orders.items()):
            plan = order.intent.plan
            if plan is None:
                continue
            if not order.filled:
                if bar.low <= plan.entry <= bar.high:
                    order.filled = True
                continue

            long = plan.direction is Direction.LONG
            hit_sl = bar.low <= plan.stop_loss if long else bar.high >= plan.stop_loss
            hit_tp = bar.high >= plan.take_profit if long else bar.low <= plan.take_profit
            if not (hit_sl or hit_tp):
                continue

            # Obchod skončil. Order z modelu MUSÍ vypadnúť: keby tu ostal ako
            # „nevyplnený", ďalší bar, ktorý pretne vstupnú cenu, by ho vyplnil
            # znova a engine by videl fantómovú pozíciu — tá blokuje opačné vstupy
            # („OPACNA POZICIA") a na konci seansy vyrobí CLOSE bez obchodu.
            del self._orders[order_id]

            # Pine počíta výhry podľa `strategy.closedtrades.profit`. Bar, ktorý
            # pretne SL aj TP, je bez 1m detailu nerozhodnuteľný — berie sa
            # konzervatívne ako strata, rovnako ako v `tradebot.tools.scan_trades`.
            if hit_tp and not hit_sl:
                day = _utc_day(bar.time)
                self._daily_wins[day] = self._daily_wins.get(day, 0) + 1

    def _apply(self, orders: list[OrderIntent]) -> None:
        for intent in orders:
            if intent.action is OrderAction.ENTRY:
                self._orders[intent.order_id] = _PendingOrder(intent)
            elif intent.action in (OrderAction.CANCEL, OrderAction.CLOSE):
                self._orders.pop(intent.order_id, None)

    # ------------------------------------------------------------------ #

    def process(self, bar: Bar, htf: HTFWindow | None) -> SignalRow:
        """Posunie engine o jeden bar a vráti riadok signálov."""
        # Pine vyhodnocuje `dailyWinLimitReached` na začiatku baru, ešte PRED tým,
        # než sa výhra z tohto baru pripočíta — limit teda platí až od ďalšieho baru.
        daily_limit = self.wins_today(bar.time) >= self.cfg.maxDailyWins
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
        self.last_ts = bar.time
        self.last_bar = bar

        row = SignalRow(
            in_trade_window=bool(out.clock and out.clock.in_trade_window),
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
            row.zone_uid = float(intent.zone_uid)

        self.rows[bar.time] = row
        if row.enter_long or row.enter_short:
            self.signal_ts.append(bar.time)
        return row

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

    def htf_window_for(self, ts_ms: int, htf_bars: dict[int, Bar], vol_sma: dict[int, float]):
        """Okno štyroch uzavretých HTF barov na bare, kde začala nová perióda — viď `HTFFeeder`.

        `htf_bars`/`vol_sma` sú predpočítané z informative dataframe; podávajú sa
        referenciou, takže opakované volanie na každom bare nič nekopíruje.
        """
        self.htf.load(htf_bars, vol_sma)
        return self.htf.window_for(ts_ms)


# --------------------------------------------------------------------------- #
# Export kresieb pre webapp
# --------------------------------------------------------------------------- #


def export_chart(runner: EngineRunner, pair: str, timeframe: str, path: Path | str) -> dict:
    """Zapíše finálny stav kresieb behu do JSON (gzip, ak cesta končí `.gz`).

    Pridá aj to, čo Pine kreslí až na poslednom bare (`barstate.islast`: S/R
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
