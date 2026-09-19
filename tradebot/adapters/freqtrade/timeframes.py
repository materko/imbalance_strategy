"""Timeframy stratégie vo Freqtrade: chýbajúci TF sa dopočíta z 1m, informatívne páry
a čo z nich burza pozná.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import IStrategy

from tradebot.core.candles import resample_ohlcv, timeframe_minutes, timeframe_name
from tradebot.core.derived import remember

logger = logging.getLogger(__name__)


class TimeframesMixin(IStrategy):
    """Chýbajúci timeframe si stratégia dopočíta z 1m; informatívne páry.
    Časť `TradebotStrategyBase`.

    Dedí z `IStrategy` kvôli hyperoptu — dôvod je pri `AIMixin` (`ai.py`)."""

    def ensure_timeframe(self, pair: str, timeframe: str) -> bool:
        """Postará sa, aby pre `pair` a `timeframe` boli sviečky na disku. Vráti, či sú.

        Freqtrade si vyšší TF **nedopočíta**: pre základný TF behu skončí na „No history …
        found", informatívny TF ticho vráti prázdny DataFrame (a stratégia potom nevytvorí
        ani jednu zónu). Chýbajúci TF sa preto poskladá z 1m — z toho istého zdroja a tým
        istým pravidlom (`tradebot.core.candles.resample_ohlcv`), aké používa graf webapp
        aj emulátor MultiCharts, takže bary sú všade rovnaké.

        Číta aj zapisuje **cez dátový handler Freqtradu**, takže pomenovanie súboru,
        formát aj `futures/` podadresár sú jeho (nič sa tu o cestách nehádže).

        Volá sa v `__init__`, teda **pred** tým, než si Freqtrade načíta dáta backtestu
        (`Backtesting.start` → `load_bt_data`), a ešte raz lenivo pri informatívnom TF.
        """
        if not self._may_derive():
            return True
        source_tf = "1m"
        try:
            from freqtrade.data.history import get_datahandler

            handler = get_datahandler(
                Path(self.config["datadir"]), self.config.get("dataformat_ohlcv", "feather")
            )
            candle_type = self.config.get("candle_type_def", "")
            have = handler.ohlcv_load(pair, timeframe, candle_type=candle_type, warn_no_data=False)
            if not have.empty:
                return True
            if timeframe == source_tf:
                return False
            minutes = timeframe_minutes(timeframe)
            base = handler.ohlcv_load(pair, source_tf, candle_type=candle_type, warn_no_data=False)
            if base.empty:
                logger.warning(
                    "%s %s: chyba %s aj %s - dopocitat sa nema z coho", self.spec.key, pair,
                    timeframe, source_tf,
                )
                return False
            out = resample_ohlcv(base[["date", "open", "high", "low", "close", "volume"]], minutes)
            handler.ohlcv_store(pair, timeframe, data=out, candle_type=candle_type)
            path = handler._pair_data_filename(
                Path(self.config["datadir"]), pair, timeframe, candle_type
            )
            remember([path])
            logger.warning(
                "%s %s: %s sviecky na disku neboli, poskladal som ich z %s (%d barov, %s). "
                "Su odvodene - do archivu nejdu.",
                self.spec.key, pair, timeframe, source_tf, len(out), path.name,
            )
            return True
        except Exception as exc:  # noqa: BLE001  (dopocet je pomoc, nie podmienka behu)
            logger.warning("%s %s: %s sa dopocitat nepodarilo (%s)", self.spec.key, pair,
                           timeframe, exc)
            return False

    def _may_derive(self) -> bool:
        """Dopočítavať sa smie len tam, kde sa počíta z histórie.

        V dry/live behu prichádzajú sviečky z burzy a vymyslený bar by bol chyba, nie pomoc.
        """
        from freqtrade.enums import RunMode

        return self.config.get("runmode") in (
            RunMode.BACKTEST, RunMode.HYPEROPT, RunMode.PLOT, RunMode.UTIL_NO_EXCHANGE,
            RunMode.UTIL_EXCHANGE, RunMode.OTHER,
        )

    def informative_frame(self, pair: str, timeframe: str) -> DataFrame:
        """Sviečky informatívneho TF; keď súbor nie je, dopočítajú sa z 1m."""
        if self.dp is None:
            return DataFrame()
        frame = self.dp.get_pair_dataframe(
            pair=pair, timeframe=timeframe, candle_type=self.config.get("candle_type_def", ""),
        )
        if frame is not None and not frame.empty:
            return frame
        if not self.ensure_timeframe(pair, timeframe):
            return DataFrame()
        frame = self.dp.get_pair_dataframe(
            pair=pair, timeframe=timeframe, candle_type=self.config.get("candle_type_def", ""),
        )
        return frame if frame is not None else DataFrame()

    def informative_pairs(self):
        """Informatívne TF stratégie (IBS: detekčný TF zón) + TF indikátorov s vlastnou predhistóriou.

        Tie druhé Freqtrade v dry/live stiahne a obnovuje spolu s TF behu (koľko sviečok,
        určuje limit burzy a `startup_candle_count`), takže pri prvom `populate_indicators`
        sú ich uzavreté bary poruke na seeding (`_live_seed_source`). TF, ktorý burza
        nepozná (3h, 45m), sa nežiada — Freqtrade by každý cyklus hlásil „Cannot download"
        — a seeding ho poskladá zo sviečok TF behu.
        """
        pairs = self.dp.current_whitelist() if self.dp else []
        tfs = list(self._informative_tfs)
        for minutes in self._seed_tfs:
            tf = timeframe_name(minutes)
            if tf not in tfs and self._exchange_has_tf(tf):
                tfs.append(tf)
        return [(p, tf) for p in pairs for tf in tfs]

    def _ft_exchange(self):
        """Burza Freqtradu za DataProviderom, alebo None (testy, nástroje bez burzy)."""
        return getattr(self.dp, "_exchange", None) if self.dp is not None else None

    def _exchange_has_tf(self, tf: str) -> bool:
        exchange = self._ft_exchange()
        if exchange is None:
            return False
        try:
            return tf in (exchange.timeframes or [])
        except Exception:  # noqa: BLE001  (burza bez zoznamu TF - radšej poskladať z TF behu)
            return False
