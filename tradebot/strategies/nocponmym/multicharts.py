"""NOC + PONDELOK 1.0 (MYM) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NocPonMymSignal"]


class NocPonMymSignal(TradebotSignal):
    STRATEGY_KEY = "nocponmym"
