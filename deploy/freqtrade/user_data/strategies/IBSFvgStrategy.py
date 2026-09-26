"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsfvg/freqtrade.py`. Tento subor je len
ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje
s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: golden_binance_btcusdt_3m;
nazov z tradebot/strategies/ibsfvg/configs alebo cesta k JSON - aj profil IBS).
"""

from tradebot.strategies.ibsfvg.freqtrade import IBSFvgStrategy as _IBSFvgStrategy


class IBSFvgStrategy(_IBSFvgStrategy):
    pass
