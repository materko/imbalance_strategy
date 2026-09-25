"""IBSNet vo Freqtrade — adaptér nad C# jadrom.

Generický `TradebotStrategyBase` volá engine cez kontrakt `on_bar`; že za ním je C#
(`tradebot.adapters.csharp.CSharpEngine`), nevie a vedieť nemusí. Čo je nad generickou
bázou vlastné IBS (HTF sviečky detekčného TF, koniec seansy, timeout limitky), sa dedí.
"""

from __future__ import annotations

from ..ibs.freqtrade import IBSImbalanceStrategy

#: `enter_tag` obchodu je ``ibsnet:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibsnet:"

__all__ = ["IBSNetStrategy", "ENTRY_TAG_PREFIX"]


class IBSNetStrategy(IBSImbalanceStrategy):
    """IBS s jadrom v C# — tie isté signály ako `IBSImbalanceStrategy`, iný engine."""

    STRATEGY_KEY = "ibsnet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
