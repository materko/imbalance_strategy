"""MTK EMAS 1.0 BTC (C# jadro) vo Freqtrade — adaptér nad C# jadrom."""

from __future__ import annotations

from ..mtkemasbtc.freqtrade import MtkEmasBtcStrategy

__all__ = ["MtkEmasBtcNetStrategy"]


class MtkEmasBtcNetStrategy(MtkEmasBtcStrategy):
    STRATEGY_KEY = "mtkemasbtcnet"
    ENTRY_TAG_PREFIX = "mtkemasbtcnet:"
