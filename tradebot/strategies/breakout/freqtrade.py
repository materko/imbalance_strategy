"""Breakout vo Freqtrade — nad generickým adaptérom len sviečky informatívneho TF.

Všetko ostatné (engine cez DataFrame, `tb_*` stĺpce, SL/TP/veľkosť z plánu, trailing,
export kresieb) je generické v `tradebot.adapters.freqtrade.base`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/BreakoutStrategy.py`.
"""

from __future__ import annotations

import logging

from tradebot.adapters.freqtrade.base import TradebotStrategyBase, _bar, _ts_ms
from tradebot.adapters.freqtrade.runner import EngineRunner
from tradebot.core import Bar

logger = logging.getLogger(__name__)

__all__ = ["BreakoutStrategy"]


class BreakoutStrategy(TradebotStrategyBase):
    """Prerazenie prvej sviečky New York openu."""

    STRATEGY_KEY = "breakout"
    ENTRY_TAG_PREFIX = "breakout:"

    timeframe = "3m"

    def _after_profile(self) -> None:
        # `tradeDirection` -> Freqtrade `can_short` (shorty vyžadujú futures trading mode).
        self.can_short = (bool(self.tb_cfg.allow_short)
                          and self.config.get("trading_mode", "spot") != "spot")

    def _feed_informative(self, runner: EngineRunner, pair: str) -> None:
        """Naplní `runner.htf` uzavretými barmi TF otváracej sviečky.

        Bez nich engine nemá high a low, na ktoré sa celá stratégia pozerá, a neurobí ani
        jeden obchod — preto je chýbajúci informative dataframe varovanie, nie ticho.
        """
        htf_bars: dict[int, Bar] = {}
        tf = self._informative_tfs[0]
        if self.dp is not None:
            # `informative_frame` súbor pre TF dopočíta z 1m, keď na disku nie je
            htf = self.informative_frame(pair, tf)
            if htf is not None and not htf.empty:
                for ts, row in zip(_ts_ms(htf["date"]), htf.itertuples(index=False)):
                    htf_bars[ts] = _bar(row, ts)
            else:
                logger.warning(
                    "Breakout: chýbajú %s dáta pre %s a nedali sa poskladať ani z 1m - "
                    "bez nich nevznikne ani jedna otváracia sviečka", tf, pair,
                )
        runner.htf.load(htf_bars)
