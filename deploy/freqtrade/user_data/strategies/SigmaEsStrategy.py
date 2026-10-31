"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sigmaes/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_5m z tradebot/strategies/sigmaes/configs).
"""

from tradebot.strategies.sigmaes.freqtrade import SigmaEsStrategy as _SigmaEsStrategy


class SigmaEsStrategy(_SigmaEsStrategy):
    pass
