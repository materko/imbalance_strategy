"""Freqtrade adaptér.

Import `strategy` ťahá `freqtrade`, takže sa robí až na požiadanie - jadro a testy
majú bežať aj bez nainštalovaného Freqtrade.
"""

from .runner import COLUMNS, EngineRunner, SignalRow

__all__ = ["EngineRunner", "SignalRow", "COLUMNS", "IBSImbalanceStrategy"]


def __getattr__(name: str):
    if name == "IBSImbalanceStrategy":
        from .strategy import IBSImbalanceStrategy

        return IBSImbalanceStrategy
    raise AttributeError(name)
