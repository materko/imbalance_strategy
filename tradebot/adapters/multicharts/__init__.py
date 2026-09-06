"""MultiCharts adaptér.

`signal` ťahá `PowerLanguage`, ktorý existuje len vnútri MultiCharts — preto sa
importuje až na požiadanie. Jadro, testy aj Freqtrade vetva musia bežať bez neho.
Názvy tried študií sú v registry (`StrategySpec.multicharts_class`) a lenivo sa
mapujú na moduly `tradebot.strategies.<key>.multicharts`.
"""

from .drawing import MCDrawSink, hex_to_rgb
from .runner import BarOutput, LiveOrder, MCRunner

__all__ = ["BarOutput", "LiveOrder", "MCDrawSink", "MCRunner", "hex_to_rgb", "TradebotSignal", "IBSSignal"]


def __getattr__(name: str):
    if name == "TradebotSignal":
        from .signal import TradebotSignal

        return TradebotSignal
    from importlib import import_module

    from ...strategies import STRATEGIES

    for spec in STRATEGIES.values():
        if name == spec.multicharts_class:
            return getattr(import_module(f"tradebot.strategies.{spec.key}.multicharts"), name)
    raise AttributeError(name)
