"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/noamym/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_5m z tradebot/strategies/noamym/configs).
"""

from tradebot.strategies.noamym.freqtrade import NoaMymStrategy as _NoaMymStrategy


class NoaMymStrategy(_NoaMymStrategy):
    pass
