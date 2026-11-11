"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/noaesnet/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_5m z tradebot/strategies/noaesnet/configs).
"""

from tradebot.strategies.noaesnet.freqtrade import NoaEsNetStrategy as _NoaEsNetStrategy


class NoaEsNetStrategy(_NoaEsNetStrategy):
    pass
