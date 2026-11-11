"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/noaes/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_5m z tradebot/strategies/noaes/configs).
"""

from tradebot.strategies.noaes.freqtrade import NoaEsStrategy as _NoaEsStrategy


class NoaEsStrategy(_NoaEsStrategy):
    pass
