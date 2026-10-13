"""IBS Entry Zone (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Generický `TradebotStrategyBase` volá engine cez kontrakt `on_bar`; že za ním je C#
(`tradebot.adapters.csharp.CSharpEngine`), nevie a vedieť nemusí. Čo je nad generickou bázou vlastné IBS
(HTF sviečky detekčného TF, koniec seansy, timeout limitky), sa dedí.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IBSEntryNetStrategy.py`.
"""

from __future__ import annotations

from ..ibsentry.freqtrade import IBSEntryZoneStrategy

#: `enter_tag` obchodu je ``ibsentrynet:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibsentrynet:"

__all__ = ["IBSEntryNetStrategy", "ENTRY_TAG_PREFIX"]


class IBSEntryNetStrategy(IBSEntryZoneStrategy):
    """IBS Entry Zone s jadrom v C# — tie isté signály ako `IBSEntryZoneStrategy`, iný engine."""

    STRATEGY_KEY = "ibsentrynet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
