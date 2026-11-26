"""MTK EMAS 1.0 ES (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkEmasEsNetSignal"]


class MtkEmasEsNetSignal(TradebotSignal):
    STRATEGY_KEY = "mtkemasesnet"
