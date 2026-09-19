"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsninja/freqtrade.py`; logika strategie bezi v C#
(`csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: golden_binance_btcusdt_3m;
nazov z tradebot/strategies/ibsninja/configs alebo cesta k JSON - aj profil IBS).
"""

from tradebot.strategies.ibsninja.freqtrade import IBSNinjaStrategy as _IBSNinjaStrategy


class IBSNinjaStrategy(_IBSNinjaStrategy):
    pass
