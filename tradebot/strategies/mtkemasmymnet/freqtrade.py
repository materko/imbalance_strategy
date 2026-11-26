"""MTK EMAS 1.0 MYM (C# jadro) vo Freqtrade — adaptér nad C# jadrom."""

from __future__ import annotations

from ..mtkemasmym.freqtrade import MtkEmasMymStrategy

__all__ = ["MtkEmasMymNetStrategy"]


class MtkEmasMymNetStrategy(MtkEmasMymStrategy):
    STRATEGY_KEY = "mtkemasmymnet"
    ENTRY_TAG_PREFIX = "mtkemasmymnet:"
