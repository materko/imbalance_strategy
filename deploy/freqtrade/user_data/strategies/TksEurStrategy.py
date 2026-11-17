"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tkseur/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: 6e_databento_3m z tradebot/strategies/tkseur/configs).
"""

from tradebot.strategies.tkseur.freqtrade import TksEurStrategy as _TksEurStrategy


class TksEurStrategy(_TksEurStrategy):
    pass
