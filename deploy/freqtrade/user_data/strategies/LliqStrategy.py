"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/lliq/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_5m z tradebot/strategies/lliq/configs).
"""

from tradebot.strategies.lliq.freqtrade import LliqStrategy as _LliqStrategy


class LliqStrategy(_LliqStrategy):
    pass
