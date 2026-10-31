"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/orb15es/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_5m z tradebot/strategies/orb15es/configs).
"""

from tradebot.strategies.orb15es.freqtrade import Orb15EsStrategy as _Orb15EsStrategy


class Orb15EsStrategy(_Orb15EsStrategy):
    pass
