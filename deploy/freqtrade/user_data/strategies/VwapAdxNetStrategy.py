"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/vwapadxnet/freqtrade.py`; logika strategie bezi v C#
(`tradebot/core/ports/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mnq_databento_1m;
nazov z tradebot/strategies/vwapadxnet/configs alebo cesta k JSON - aj profil VWAP ADX).
"""

from tradebot.strategies.vwapadxnet.freqtrade import VwapAdxNetStrategy as _VwapAdxNetStrategy


class VwapAdxNetStrategy(_VwapAdxNetStrategy):
    pass
