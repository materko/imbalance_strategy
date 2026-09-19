"""IBSNinja vo Freqtrade — adaptér nad C# jadrom.

Generický `TradebotStrategyBase` volá engine cez kontrakt `on_bar`; že za ním je C#
(`tradebot.adapters.csharp.CSharpEngine`), nevie a vedieť nemusí. Čo je nad generickou
bázou vlastné IBS (HTF sviečky detekčného TF, koniec seansy, timeout limitky), sa dedí.
"""

from __future__ import annotations

from ..ibs.freqtrade import IBSImbalanceStrategy

#: `enter_tag` obchodu je ``ibsninja:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibsninja:"

__all__ = ["IBSNinjaStrategy", "ENTRY_TAG_PREFIX"]


class IBSNinjaStrategy(IBSImbalanceStrategy):
    """IBS s jadrom v C# — tie isté signály ako `IBSImbalanceStrategy`, iný engine."""

    STRATEGY_KEY = "ibsninja"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
