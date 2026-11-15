"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/wpreur/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: 6e_databento_15m z tradebot/strategies/wpreur/configs).
"""

from tradebot.strategies.wpreur.freqtrade import WprEurStrategy as _WprEurStrategy


class WprEurStrategy(_WprEurStrategy):
    pass
