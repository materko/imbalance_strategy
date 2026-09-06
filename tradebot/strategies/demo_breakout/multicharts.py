"""Demo Donchian Breakout v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `platforms/multicharts/DemoBreakout_Signal.py`.
Stratégia nemá informatívny TF, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["DemoBreakoutSignal"]


class DemoBreakoutSignal(TradebotSignal):
    STRATEGY_KEY = "demo_breakout"
