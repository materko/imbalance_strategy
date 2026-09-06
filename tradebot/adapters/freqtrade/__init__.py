"""Freqtrade adaptér.

Import stratégií ťahá `freqtrade`, takže sa robí až na požiadanie — jadro a testy
majú bežať aj bez nainštalovaného Freqtrade. Názvy tried sú v registry
(`StrategySpec.freqtrade_class`), tu sa lenivo mapujú na moduly
`tradebot.strategies.<key>.freqtrade`.
"""

from .runner import COLUMN_ATTRS, COLUMNS, EngineRunner, SignalRow, export_chart

__all__ = ["EngineRunner", "SignalRow", "COLUMNS", "COLUMN_ATTRS", "export_chart", "TradebotStrategyBase"]


def __getattr__(name: str):
    if name == "TradebotStrategyBase":
        from .base import TradebotStrategyBase

        return TradebotStrategyBase
    from importlib import import_module

    from ...strategies import STRATEGIES

    for spec in STRATEGIES.values():
        if name == spec.freqtrade_class:
            return getattr(import_module(f"tradebot.strategies.{spec.key}.freqtrade"), name)
    raise AttributeError(name)
