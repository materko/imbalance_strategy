"""VWAP ORB (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Generický `TradebotStrategyBase` volá engine cez kontrakt `on_bar`; že za ním je C#
(`tradebot.adapters.csharp.CSharpEngine`), nevie a vedieť nemusí. `tradeDirection` -> `can_short` sa dedí.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/VwapOrbNetStrategy.py`.
"""

from __future__ import annotations

from ..vwaporb.freqtrade import VwapOrbStrategy

#: `enter_tag` obchodu je ``vwaporbnet:<…>``.
ENTRY_TAG_PREFIX = "vwaporbnet:"

__all__ = ["VwapOrbNetStrategy", "ENTRY_TAG_PREFIX"]


class VwapOrbNetStrategy(VwapOrbStrategy):
    """VWAP ORB s jadrom v C# — tie isté signály ako `VwapOrbStrategy`, iný engine."""

    STRATEGY_KEY = "vwaporbnet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "5m"
