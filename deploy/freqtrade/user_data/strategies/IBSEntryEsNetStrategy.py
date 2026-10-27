"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsentryesnet/freqtrade.py`; logika strategie bezi v C#
(`tradebot/core/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: PRESIEL_SMERNICAMI_IBS_EZ_ES_1;
nazov z tradebot/strategies/ibsentryesnet/configs alebo cesta k JSON).
"""

from tradebot.strategies.ibsentryesnet.freqtrade import IBSEntryEsNetStrategy as _IBSEntryEsNetStrategy


class IBSEntryEsNetStrategy(_IBSEntryEsNetStrategy):
    pass
