"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tksmgc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mgc_databento_3m z tradebot/strategies/tksmgc/configs).
"""

from tradebot.strategies.tksmgc.freqtrade import TksMgcStrategy as _TksMgcStrategy


class TksMgcStrategy(_TksMgcStrategy):
    pass
