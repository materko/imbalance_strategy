"""MTK EMAS 1.0 MGC (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkEmasMgcNetSignal"]


class MtkEmasMgcNetSignal(TradebotSignal):
    STRATEGY_KEY = "mtkemasmgcnet"
