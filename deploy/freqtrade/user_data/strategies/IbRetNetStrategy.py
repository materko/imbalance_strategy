"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibretnet/freqtrade.py`; logika strategie bezi v C#
(`tradebot/core/ports/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mnq_databento_5m;
nazov z tradebot/strategies/ibretnet/configs alebo cesta k JSON - aj profil IB RETRACE 1.0).
"""

from tradebot.strategies.ibretnet.freqtrade import IbRetNetStrategy as _IbRetNetStrategy


class IbRetNetStrategy(_IbRetNetStrategy):
    pass
