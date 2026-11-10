"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/mtkzonenet/freqtrade.py`; logika strategie bezi v C#
(`tradebot/core/ports/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mnq_databento_3m;
nazov z tradebot/strategies/mtkzonenet/configs alebo cesta k JSON - aj profil VWAP ADX).
"""

from tradebot.strategies.mtkzonenet.freqtrade import MtkZoneNetStrategy as _MtkZoneNetStrategy


class MtkZoneNetStrategy(_MtkZoneNetStrategy):
    pass
