"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/wpres/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_15m z tradebot/strategies/wpres/configs).
"""

from tradebot.strategies.wpres.freqtrade import WprEsStrategy as _WprEsStrategy


class WprEsStrategy(_WprEsStrategy):
    pass
