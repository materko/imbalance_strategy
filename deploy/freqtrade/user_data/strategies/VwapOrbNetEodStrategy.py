"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/vwaporbneteod/freqtrade.py`; logika strategie bezi v C#
(`csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: mnq_databento_5m;
nazov z tradebot/strategies/vwaporbneteod/configs alebo cesta k JSON).
"""

from tradebot.strategies.vwaporbneteod.freqtrade import VwapOrbNetEodStrategy as _VwapOrbNetEodStrategy


class VwapOrbNetEodStrategy(_VwapOrbNetEodStrategy):
    pass
