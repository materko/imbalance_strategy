"""Spätná kompatibilita — IBS Freqtrade stratégia žije v `tradebot.strategies.ibs.freqtrade`.

Generická báza pre všetky stratégie je `tradebot.adapters.freqtrade.base.TradebotStrategyBase`.
"""

from tradebot.strategies.ibs.freqtrade import ENTRY_TAG_PREFIX, IBSImbalanceStrategy

__all__ = ["IBSImbalanceStrategy", "ENTRY_TAG_PREFIX"]
