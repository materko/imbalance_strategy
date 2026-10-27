"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/noanet/freqtrade.py`; logika strategie bezi v C#
(`tradebot/core/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mnq_databento_5m;
nazov z tradebot/strategies/noanet/configs alebo cesta k JSON - aj profil NOA 1.0).
"""

from tradebot.strategies.noanet.freqtrade import NoaNetStrategy as _NoaNetStrategy


class NoaNetStrategy(_NoaNetStrategy):
    pass
