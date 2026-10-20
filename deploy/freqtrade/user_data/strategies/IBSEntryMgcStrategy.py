"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsentrymgc/freqtrade.py`. Tento subor je len
ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje
s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mgc_databento_3m;
nazov z tradebot/strategies/ibsentrymgc/configs alebo cesta k JSON - aj profil IBS).
"""

from tradebot.strategies.ibsentrymgc.freqtrade import IBSEntryMgcStrategy as _IBSEntryMgcStrategy


class IBSEntryMgcStrategy(_IBSEntryMgcStrategy):
    pass
