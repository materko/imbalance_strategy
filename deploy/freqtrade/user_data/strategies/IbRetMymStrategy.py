"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibretmym/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_5m z tradebot/strategies/ibretmym/configs).
"""

from tradebot.strategies.ibretmym.freqtrade import IbRetMymStrategy as _IbRetMymStrategy


class IbRetMymStrategy(_IbRetMymStrategy):
    pass
