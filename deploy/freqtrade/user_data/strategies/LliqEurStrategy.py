"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/lliqeur/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: 6e_databento_5m z tradebot/strategies/lliqeur/configs).
"""

from tradebot.strategies.lliqeur.freqtrade import LliqEurStrategy as _LliqEurStrategy


class LliqEurStrategy(_LliqEurStrategy):
    pass
