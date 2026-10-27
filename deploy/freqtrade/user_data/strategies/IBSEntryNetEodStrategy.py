"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibsentryneteod/freqtrade.py`; logika strategie bezi v C#
(`tradebot/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: golden_binance_btcusdt_3m;
nazov z tradebot/strategies/ibsentryneteod/configs alebo cesta k JSON).
"""

from tradebot.strategies.ibsentryneteod.freqtrade import IBSEntryNetEodStrategy as _IBSEntryNetEodStrategy


class IBSEntryNetEodStrategy(_IBSEntryNetEodStrategy):
    pass
