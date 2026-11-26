"""MTK EMAS 1.0 MGC (C# jadro) vo Freqtrade — adaptér nad C# jadrom."""

from __future__ import annotations

from ..mtkemasmgc.freqtrade import MtkEmasMgcStrategy

__all__ = ["MtkEmasMgcNetStrategy"]


class MtkEmasMgcNetStrategy(MtkEmasMgcStrategy):
    STRATEGY_KEY = "mtkemasmgcnet"
    ENTRY_TAG_PREFIX = "mtkemasmgcnet:"
