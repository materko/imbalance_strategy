"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tksnet/freqtrade.py`; logika strategie bezi v C#
(`csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mnq_databento_3m;
nazov z tradebot/strategies/tksnet/configs alebo cesta k JSON - aj profil TKS 1.0).
"""

from tradebot.strategies.tksnet.freqtrade import TksNetStrategy as _TksNetStrategy


class TksNetStrategy(_TksNetStrategy):
    pass
