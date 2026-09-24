"""ORBNinja vo Freqtrade — adaptér nad C# jadrom.

Generický `TradebotStrategyBase` volá engine cez kontrakt `on_bar`; že za ním je C#
(`tradebot.adapters.csharp.CSharpEngine`), nevie a vedieť nemusí. Čo je nad generickou
bázou vlastné ORB (`tradeDirection` -> `can_short`), sa dedí.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/ORBNinjaStrategy.py`.
"""

from __future__ import annotations

from ..orb.freqtrade import ORBStrategy

#: `enter_tag` obchodu je ``orbninja:<…>``.
ENTRY_TAG_PREFIX = "orbninja:"

__all__ = ["ORBNinjaStrategy", "ENTRY_TAG_PREFIX"]


class ORBNinjaStrategy(ORBStrategy):
    """ORB s jadrom v C# — tie isté signály ako `ORBStrategy`, iný engine."""

    STRATEGY_KEY = "orbninja"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
