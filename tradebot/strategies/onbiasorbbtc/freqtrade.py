"""Overnight Bias ORB (BTC) vo Freqtrade — tie isté signály ako `OnBiasOrbStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/OnBiasOrbBtcStrategy.py`.
"""

from __future__ import annotations

from ..onbiasorb.freqtrade import OnBiasOrbStrategy

__all__ = ["OnBiasOrbBtcStrategy"]


class OnBiasOrbBtcStrategy(OnBiasOrbStrategy):
    STRATEGY_KEY = "onbiasorbbtc"
    ENTRY_TAG_PREFIX = "onbiasorbbtc:"

    timeframe = "15m"
