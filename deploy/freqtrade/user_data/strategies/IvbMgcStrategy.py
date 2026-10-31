"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ivbmgc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mgc_databento_5m z tradebot/strategies/ivbmgc/configs).
"""

from tradebot.strategies.ivbmgc.freqtrade import IvbMgcStrategy as _IvbMgcStrategy


class IvbMgcStrategy(_IvbMgcStrategy):
    pass
