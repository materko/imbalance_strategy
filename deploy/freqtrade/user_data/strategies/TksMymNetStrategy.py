"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tksmymnet/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_3m z tradebot/strategies/tksmymnet/configs).
"""

from tradebot.strategies.tksmymnet.freqtrade import TksMymNetStrategy as _TksMymNetStrategy


class TksMymNetStrategy(_TksMymNetStrategy):
    pass
