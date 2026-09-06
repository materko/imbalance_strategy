"""MultiCharts adaptér.

`signal` ťahá `PowerLanguage`, ktorý existuje len vnútri MultiCharts — preto sa
importuje až na požiadanie. Jadro, testy aj Freqtrade vetva musia bežať bez neho.
"""

from .drawing import MCDrawSink, hex_to_rgb
from .runner import BarOutput, LiveOrder, MCRunner

__all__ = ["BarOutput", "LiveOrder", "MCDrawSink", "MCRunner", "hex_to_rgb", "IBSSignal"]


def __getattr__(name: str):
    if name == "IBSSignal":
        from .signal import IBSSignal

        return IBSSignal
    raise AttributeError(name)
