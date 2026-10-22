"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsentryes/freqtrade.py`. Tento subor je len
ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje
s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: es_databento_3m;
nazov z tradebot/strategies/ibsentryes/configs alebo cesta k JSON - aj profil IBS).
"""

from tradebot.strategies.ibsentryes.freqtrade import IBSEntryEsStrategy as _IBSEntryEsStrategy


class IBSEntryEsStrategy(_IBSEntryEsStrategy):
    pass
