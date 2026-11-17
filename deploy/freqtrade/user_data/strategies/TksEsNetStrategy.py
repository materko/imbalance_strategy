"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tksesnet/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_3m z tradebot/strategies/tksesnet/configs).
"""

from tradebot.strategies.tksesnet.freqtrade import TksEsNetStrategy as _TksEsNetStrategy


class TksEsNetStrategy(_TksEsNetStrategy):
    pass
