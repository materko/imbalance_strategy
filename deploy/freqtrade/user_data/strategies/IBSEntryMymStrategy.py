"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsentrymym/freqtrade.py`. Tento subor je len
ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje
s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mym_databento_3m;
nazov z tradebot/strategies/ibsentrymym/configs alebo cesta k JSON - aj profil IBS).
"""

from tradebot.strategies.ibsentrymym.freqtrade import IBSEntryMymStrategy as _IBSEntryMymStrategy


class IBSEntryMymStrategy(_IBSEntryMymStrategy):
    pass
