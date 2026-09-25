"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsentry/freqtrade.py`. Tento subor je len
ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje
s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: golden_binance_btcusdt_3m;
nazov z tradebot/strategies/ibsentry/configs alebo cesta k JSON - aj profil IBS).
"""

from tradebot.strategies.ibsentry.freqtrade import IBSEntryZoneStrategy as _IBSEntryZoneStrategy


class IBSEntryZoneStrategy(_IBSEntryZoneStrategy):
    pass
