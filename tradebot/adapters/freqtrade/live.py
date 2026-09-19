"""Beh naživo (dry/live): engine sa pred prvou sviečkou nasýti históriou zo súboru
alebo z burzy a medzery vo feede sa hlásia.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import IStrategy

from tradebot.core.candles import timeframe_minutes, timeframe_name
from tradebot.core.warmup import WarmupNeed, seed_engine

from .frames import _between
from .runner import EngineRunner

logger = logging.getLogger(__name__)


class LiveMixin(IStrategy):
    """Štart naživo: seed enginu históriou a medzery vo feede. Časť `TradebotStrategyBase`.

    Dedí z `IStrategy` kvôli hyperoptu — dôvod je pri `AIMixin` (`ai.py`)."""

    @property
    def live_mode(self) -> bool:
        """Dry-run alebo live: sviečky prichádzajú od burzy cez DataProvider, nie z disku."""
        from freqtrade.enums import RunMode

        return self.config.get("runmode") in (RunMode.DRY_RUN, RunMode.LIVE)

    def _live_gap(self, runner: EngineRunner, pair: str, ts_index: list[int]) -> bool:
        """Dry/live: DataFrame už nenadväzuje na posledný spracovaný bar (výpadok spojenia,
        uspatý stroj, „Time jump detected" vo Freqtrade). Inkrementálny runner by dieru
        preskočil, preto sa postaví nanovo — s predhistóriou a seedingom ako po reštarte."""
        if runner.last_ts is None or not ts_index:
            return False
        step = timeframe_minutes(self.run_timeframe) * 60_000
        if ts_index[0] <= runner.last_ts + step:
            return False
        logger.warning("%s %s: sviecky od burzy nenadvazuju na posledny spracovany bar (diera %d min) "
                       "- runner sa stavia nanovo s predhistoriou", self.spec.key, pair,
                       (ts_index[0] - runner.last_ts - step) // 60_000)
        return True

    def _seed_runner(self, runner: EngineRunner, pair: str, ts_index: list[int]) -> int:
        """Indikátory s vlastnou predhistóriou (Supertrend/ADX na svojom TF) pred prvým barom.

        Vracia index riadku DataFrame, od ktorého runner beží (riadky pred ním sú len zdroj
        predhistórie a signál nedostanú). Seeding je jeden (`seed_engine`), líši sa len zdroj:

        * **backtest a hyperopt** — sviečky TF behu **pred** prvým riadkom DataFrame (ten už
          obsahuje `startup_candle_count`) z disku cez dátový handler Freqtradu, bez vypchávky;
          runner beží od riadku 0.
        * **dry-run a live** — DataFrame od burzy má aspoň `startup_candle_count + 1` sviečok
          (Freqtrade ich stiahne pri štarte aj po reštarte, viac volaní, keď je limit burzy
          menší). Runner začne na prvom riadku zarovnanom na periódy TF indikátorov, ak za ním
          ostane celá predhistória (`_live_start`) — rozpracovaná perióda je potom prázdna a
          netreba nič sťahovať. Uzavreté bary TF indikátora dá DataProvider
          (`informative_pairs`); čo nedá (TF, ktorý burza nepozná, alebo pre limit burzy
          málo sviečok) a rozpracovanú periódu pri nezarovnanom štarte stiahne
          `_seed_download` ako sviečky TF behu z burzy. Nič od prvého baru ďalej sa nepoužije.
        """
        warmup = getattr(runner.engine, "warmup", None)
        if warmup is None or not warmup.seeds:
            return 0
        used: dict[str, str] = {}
        if self.live_mode:
            start = self._live_start(ts_index, warmup.seeds)
            source = self._live_seed_source(pair, ts_index[start], used)
        else:
            start = 0
            source = None
            if self._may_derive():
                key = (pair, ts_index[0], warmup.seed_span_ms, self.run_timeframe)
                if key not in self._seed_frames:
                    self._seed_frames[key] = self._load_before(pair, ts_index[0], warmup.seed_span_ms)
                source = self._seed_frames[key]
        try:
            got = seed_engine(runner.engine, source, ts_index[start])
        finally:
            self._seed_downloads.clear()
        if start:
            logger.info("%s %s: beh zacina %d. sviecku DataFrame od burzy (zarovnane na periody "
                        "indikatorov, za nou %d sviecok)", self.spec.key, pair, start,
                        len(ts_index) - start)
        short = [f"{n.name} @{n.tf_minutes}m {got.get(n.name, 0)}/{n.bars}"
                 for n in warmup.seeds if got.get(n.name, 0) < n.bars]
        where = f" ({', '.join(f'{k}: {v}' for k, v in used.items())})" if used else ""
        if short:
            logger.warning("%s %s: predhistoria indikatorov pred behom neuplna (%s)%s - rozbehnu sa "
                           "na grafe, dovtedy neobchoduju", self.spec.key, pair, ", ".join(short), where)
        else:
            logger.info("%s %s: indikatory seedovane pred behom (%s)%s", self.spec.key, pair,
                        ", ".join(f"{k} {v}" for k, v in got.items()), where)
        return start

    def _live_start(self, ts_index: list[int], seeds: list[WarmupNeed]) -> int:
        """Prvý riadok zarovnaný na periódy všetkých TF indikátorov, za ktorým ostane
        `startup_candle_count` sviečok predhistórie + posledná; inak 0 (začiatok DataFrame)."""
        align = 1
        for need in seeds:
            align = math.lcm(align, int(need.tf_minutes))
        align_ms = align * 60_000
        last = len(ts_index) - (int(self.startup_candle_count or 0) + 1)
        for k in range(0, last + 1):
            if ts_index[k] % align_ms == 0:
                return k
        return 0

    def _live_seed_source(self, pair: str, first_ms: int, used: dict[str, str]):
        """`need -> DataFrame` pre `seed_engine` v dry/live: uzavreté bary + rozpracovaná perióda.

        Uzavreté periódy (pred periódou `first_ms`) prednostne ako sviečky TF indikátora od
        DataProvidera; ak ich burza nemá alebo ich je menej než `warmup_bars`, sviečky TF behu
        z burzy. Rozpracovaná perióda `[perióda, first_ms)` je vždy v TF behu. Bary sa na TF
        indikátora skladajú v `seed_engine` cez `tradebot.core.candles` ako v backteste.
        """
        import pandas as pd

        run_tf = self.run_timeframe

        def source(need: WarmupNeed):
            ms = int(need.tf_minutes) * 60_000
            period = first_ms // ms * ms
            since = period - need.span_ms
            closed = self._exchange_closed(pair, need, since, period)
            if closed is not None:
                used[need.name] = f"{len(closed)} x {timeframe_name(need.tf_minutes)} od burzy"
            else:
                closed = self._seed_download(pair, since, period)
                used[need.name] = f"{0 if closed is None else len(closed)} x {run_tf} z historie burzy"
            partial = self._seed_download(pair, period, first_ms) if period < first_ms else None
            parts = [f for f in (closed, partial) if f is not None and len(f)]
            return pd.concat(parts, ignore_index=True) if parts else None

        return source

    def _exchange_closed(self, pair: str, need: WarmupNeed, since_ms: int, until_ms: int) -> DataFrame | None:
        """Uzavreté bary TF indikátora v `[since_ms, until_ms)` od DataProvidera, ak ich je dosť."""
        tf = timeframe_name(need.tf_minutes)
        if self.dp is None or not self._exchange_has_tf(tf):
            return None
        try:
            frame = self.dp.get_pair_dataframe(pair=pair, timeframe=tf,
                                               candle_type=self.config.get("candle_type_def", ""))
        except Exception as exc:  # noqa: BLE001 (náhradná cesta sú sviečky TF behu)
            logger.warning("%s %s: %s od burzy nie su (%s)", self.spec.key, pair, tf, exc)
            return None
        part = _between(frame, since_ms, until_ms)
        if part is None or len(part) < need.bars:
            return None
        return part

    def _seed_download(self, pair: str, since_ms: int, until_ms: int) -> DataFrame | None:
        """Sviečky TF behu v `[since_ms, until_ms)` stiahnuté z burzy (len pri štarte runnera).

        `Exchange.get_historic_ohlcv` stránkuje po limite burzy sám. Burza bez histórie
        (Kraken) alebo výpadok vráti None — indikátor sa potom rozbehne na grafe.
        """
        key = (pair, since_ms, until_ms)
        if key in self._seed_downloads:
            return self._seed_downloads[key]
        frame = None
        exchange = self._ft_exchange()
        if exchange is not None and until_ms > since_ms:
            try:
                from freqtrade.enums import CandleType

                raw = exchange.get_historic_ohlcv(
                    pair=pair, timeframe=self.run_timeframe, since_ms=int(since_ms),
                    candle_type=self.config.get("candle_type_def") or CandleType.SPOT,
                    until_ms=int(until_ms),
                )
                frame = _between(raw, since_ms, until_ms)
            except Exception as exc:  # noqa: BLE001 (seeding je pomoc; bez neho sa indikátor rozbehne sám)
                logger.warning("%s %s: historia %s z burzy sa nestiahla (%s)", self.spec.key, pair,
                               self.run_timeframe, exc)
        self._seed_downloads[key] = frame
        return frame

    def _load_before(self, pair: str, first_ms: int, span_ms: int) -> DataFrame | None:
        """Sviečky TF behu v `[first_ms - span_ms, first_ms)` z disku, alebo None."""
        try:
            from freqtrade.configuration import TimeRange
            from freqtrade.data.history import get_datahandler

            handler = get_datahandler(
                Path(self.config["datadir"]), self.config.get("dataformat_ohlcv", "feather")
            )
            start_s = (first_ms - span_ms) // 1000
            timerange = TimeRange("date", "date", start_s, max(start_s, first_ms // 1000 - 1))
            frame = handler.ohlcv_load(pair, self.run_timeframe,
                                       candle_type=self.config.get("candle_type_def", ""),
                                       timerange=timerange, fill_missing=False, warn_no_data=False)
            return frame if frame is not None and not frame.empty else None
        except Exception as exc:  # noqa: BLE001 (seeding je pomoc; bez neho sa indikátor rozbehne sám)
            logger.warning("%s %s: sviecky pred behom sa nenacitali (%s)", self.spec.key, pair, exc)
            return None
