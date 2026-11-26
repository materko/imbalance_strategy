"""MTK EMAS 1.0 ES (C# jadro) vo Freqtrade — adaptér nad C# jadrom."""

from __future__ import annotations

from ..mtkemases.freqtrade import MtkEmasEsStrategy

__all__ = ["MtkEmasEsNetStrategy"]


class MtkEmasEsNetStrategy(MtkEmasEsStrategy):
    STRATEGY_KEY = "mtkemasesnet"
    ENTRY_TAG_PREFIX = "mtkemasesnet:"
