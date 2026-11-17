"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tkses/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_3m z tradebot/strategies/tkses/configs).
"""

from tradebot.strategies.tkses.freqtrade import TksEsStrategy as _TksEsStrategy


class TksEsStrategy(_TksEsStrategy):
    pass
