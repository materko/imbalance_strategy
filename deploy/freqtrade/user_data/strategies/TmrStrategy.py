"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tmr/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_15m z tradebot/strategies/tmr/configs).
"""

from tradebot.strategies.tmr.freqtrade import TmrStrategy as _TmrStrategy


class TmrStrategy(_TmrStrategy):
    pass
