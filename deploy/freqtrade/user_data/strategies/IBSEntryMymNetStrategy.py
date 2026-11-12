"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsentrymymnet/freqtrade.py`; logika strategie bezi v C#
(`tradebot/core/ports/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mym_databento_3m;
nazov z tradebot/strategies/ibsentrymymnet/configs alebo cesta k JSON).
"""

from tradebot.strategies.ibsentrymymnet.freqtrade import IBSEntryMymNetStrategy as _IBSEntryMymNetStrategy


class IBSEntryMymNetStrategy(_IBSEntryMymNetStrategy):
    pass
