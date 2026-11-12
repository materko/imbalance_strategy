"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/lliqmym/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_5m z tradebot/strategies/lliqmym/configs).
"""

from tradebot.strategies.lliqmym.freqtrade import LliqMymStrategy as _LliqMymStrategy


class LliqMymStrategy(_LliqMymStrategy):
    pass
