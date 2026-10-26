"""SD ZÓNY EURUSD v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/SdEur_Signal.py`. Na grafe stačí Data1 (zóny sa skladajú zo sviečok grafu).
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SdEurSignal"]


class SdEurSignal(TradebotSignal):
    STRATEGY_KEY = "sdeur"
