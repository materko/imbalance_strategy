"""Mag7 + SPX sila v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Mag7_Signal.py`. Symboly sily číta feeder z 1m skladu sviečok, ktorý
živá študia na počítači s MultiCharts nemá — tam sila nevznikne (emulátor vo webapp áno).
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["Mag7Signal"]


class Mag7Signal(TradebotSignal):
    STRATEGY_KEY = "mag7"
