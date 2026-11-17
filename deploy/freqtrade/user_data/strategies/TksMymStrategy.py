"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tksmym/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_3m z tradebot/strategies/tksmym/configs).
"""

from tradebot.strategies.tksmym.freqtrade import TksMymStrategy as _TksMymStrategy


class TksMymStrategy(_TksMymStrategy):
    pass
