"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tmrmym/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_15m z tradebot/strategies/tmrmym/configs).
"""

from tradebot.strategies.tmrmym.freqtrade import TmrMymStrategy as _TmrMymStrategy


class TmrMymStrategy(_TmrMymStrategy):
    pass
