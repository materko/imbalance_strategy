"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/nqpreces/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_1m z tradebot/strategies/nqpreces/configs).
"""

from tradebot.strategies.nqpreces.freqtrade import NqprecEsStrategy as _NqprecEsStrategy


class NqprecEsStrategy(_NqprecEsStrategy):
    pass
