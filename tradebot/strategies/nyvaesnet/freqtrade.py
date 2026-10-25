"""NY VA BREAKOUT ES (C# jadro) vo Freqtrade — tie isté signály ako `NyVaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NyVaEsNetStrategy.py`.
"""

from __future__ import annotations

from ..nyvaes.freqtrade import NyVaEsStrategy

__all__ = ["NyVaEsNetStrategy"]


class NyVaEsNetStrategy(NyVaEsStrategy):
    STRATEGY_KEY = "nyvaesnet"
    ENTRY_TAG_PREFIX = "nyvaesnet:"
