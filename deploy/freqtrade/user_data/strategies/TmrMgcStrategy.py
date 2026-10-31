"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tmrmgc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mgc_databento_15m z tradebot/strategies/tmrmgc/configs).
"""

from tradebot.strategies.tmrmgc.freqtrade import TmrMgcStrategy as _TmrMgcStrategy


class TmrMgcStrategy(_TmrMgcStrategy):
    pass
