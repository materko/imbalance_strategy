"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/lliqes/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_5m z tradebot/strategies/lliqes/configs).
"""

from tradebot.strategies.lliqes.freqtrade import LliqEsStrategy as _LliqEsStrategy


class LliqEsStrategy(_LliqEsStrategy):
    pass
