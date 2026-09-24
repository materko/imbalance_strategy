"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/orbninja/freqtrade.py`; logika strategie bezi v C#
(`csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: nas100_dukascopy_3m;
nazov z tradebot/strategies/orbninja/configs alebo cesta k JSON - aj profil ORB).
"""

from tradebot.strategies.orbninja.freqtrade import ORBNinjaStrategy as _ORBNinjaStrategy


class ORBNinjaStrategy(_ORBNinjaStrategy):
    pass
