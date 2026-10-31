"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/orb15mgc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mgc_databento_5m z tradebot/strategies/orb15mgc/configs).
"""

from tradebot.strategies.orb15mgc.freqtrade import Orb15MgcStrategy as _Orb15MgcStrategy


class Orb15MgcStrategy(_Orb15MgcStrategy):
    pass
