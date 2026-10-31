"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/nqprec/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_1m z tradebot/strategies/nqprec/configs).
"""

from tradebot.strategies.nqprec.freqtrade import NqprecStrategy as _NqprecStrategy


class NqprecStrategy(_NqprecStrategy):
    pass
