"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/nqprecmgc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mgc_databento_1m z tradebot/strategies/nqprecmgc/configs).
"""

from tradebot.strategies.nqprecmgc.freqtrade import NqprecMgcStrategy as _NqprecMgcStrategy


class NqprecMgcStrategy(_NqprecMgcStrategy):
    pass
