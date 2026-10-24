"""NY VA SHAPE vo Freqtrade — tie isté signály ako `NyVaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NyVaShapeStrategy.py`.
"""

from __future__ import annotations

from ..nyva.freqtrade import NyVaStrategy

__all__ = ["NyVaShapeStrategy"]


class NyVaShapeStrategy(NyVaStrategy):
    STRATEGY_KEY = "nyvashape"
    ENTRY_TAG_PREFIX = "nyvashape:"
