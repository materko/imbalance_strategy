"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/vwapadxneteod/freqtrade.py`; logika strategie bezi v C#
(`tradebot/core/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mnq_databento_1m;
nazov z tradebot/strategies/vwapadxneteod/configs alebo cesta k JSON).
"""

from tradebot.strategies.vwapadxneteod.freqtrade import VwapAdxNetEodStrategy as _VwapAdxNetEodStrategy


class VwapAdxNetEodStrategy(_VwapAdxNetEodStrategy):
    pass
