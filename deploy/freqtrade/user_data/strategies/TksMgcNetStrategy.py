"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tksmgcnet/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mgc_databento_3m z tradebot/strategies/tksmgcnet/configs).
"""

from tradebot.strategies.tksmgcnet.freqtrade import TksMgcNetStrategy as _TksMgcNetStrategy


class TksMgcNetStrategy(_TksMgcNetStrategy):
    pass
