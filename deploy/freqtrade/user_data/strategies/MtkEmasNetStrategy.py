"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/mtkemasnet/freqtrade.py`; logika strategie bezi v C#
(`tradebot/core/ports/csharp/`) cez most `tradebot/adapters/csharp`. Tento subor je len ukazovatel - Freqtrade
resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil sa prepina premennou prostredia TRADEBOT_PROFILE (default: default;
nazov z tradebot/strategies/mtkemasnet/configs alebo cesta k JSON - aj profil MTK EMAS 1.0).
"""

from tradebot.strategies.mtkemasnet.freqtrade import MtkEmasNetStrategy as _MtkEmasNetStrategy


class MtkEmasNetStrategy(_MtkEmasNetStrategy):
    pass
