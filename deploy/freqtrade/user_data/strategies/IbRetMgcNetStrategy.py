"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ibretmgcnet/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mgc_databento_5m z tradebot/strategies/ibretmgcnet/configs).
"""

from tradebot.strategies.ibretmgcnet.freqtrade import IbRetMgcNetStrategy as _IbRetMgcNetStrategy


class IbRetMgcNetStrategy(_IbRetMgcNetStrategy):
    pass
