"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/vwaporbnet/freqtrade.py`; logika strategie bezi v C#
(`tradebot/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mnq_databento_5m;
nazov z tradebot/strategies/vwaporbnet/configs alebo cesta k JSON - aj profil VWAP ORB).
"""

from tradebot.strategies.vwaporbnet.freqtrade import VwapOrbNetStrategy as _VwapOrbNetStrategy


class VwapOrbNetStrategy(_VwapOrbNetStrategy):
    pass
