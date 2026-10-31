"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tmres/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_15m z tradebot/strategies/tmres/configs).
"""

from tradebot.strategies.tmres.freqtrade import TmrEsStrategy as _TmrEsStrategy


class TmrEsStrategy(_TmrEsStrategy):
    pass
