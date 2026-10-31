"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/ivbes/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_5m z tradebot/strategies/ivbes/configs).
"""

from tradebot.strategies.ivbes.freqtrade import IvbEsStrategy as _IvbEsStrategy


class IvbEsStrategy(_IvbEsStrategy):
    pass
