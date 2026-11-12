"""NOC + PONDELOK 1.0 (MYM) vo Freqtrade — tie isté signály ako `NocPonStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NocPonMymStrategy.py`.
"""

from __future__ import annotations

from ..nocpon.freqtrade import NocPonStrategy

__all__ = ["NocPonMymStrategy"]


class NocPonMymStrategy(NocPonStrategy):
    STRATEGY_KEY = "nocponmym"
    ENTRY_TAG_PREFIX = "nocponmym:"

    timeframe = "5m"
