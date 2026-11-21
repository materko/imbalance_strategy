"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibretmymnet/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_5m z tradebot/strategies/ibretmymnet/configs).
"""

from tradebot.strategies.ibretmymnet.freqtrade import IbRetMymNetStrategy as _IbRetMymNetStrategy


class IbRetMymNetStrategy(_IbRetMymNetStrategy):
    pass
