"""NY VA BREAKOUT ES vo Freqtrade — tie isté signály ako `NyVaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NyVaEsStrategy.py`.
"""

from __future__ import annotations

from ..nyva.freqtrade import NyVaStrategy

__all__ = ["NyVaEsStrategy"]


class NyVaEsStrategy(NyVaStrategy):
    STRATEGY_KEY = "nyvaes"
    ENTRY_TAG_PREFIX = "nyvaes:"
