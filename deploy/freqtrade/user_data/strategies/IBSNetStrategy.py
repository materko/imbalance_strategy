"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsnet/freqtrade.py`; logika strategie bezi v C#
(`csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: golden_binance_btcusdt_3m;
nazov z tradebot/strategies/ibsnet/configs alebo cesta k JSON - aj profil IBS).
"""

from tradebot.strategies.ibsnet.freqtrade import IBSNetStrategy as _IBSNetStrategy


class IBSNetStrategy(_IBSNetStrategy):
    pass
