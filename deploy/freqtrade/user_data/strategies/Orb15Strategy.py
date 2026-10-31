"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/orb15/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_5m z tradebot/strategies/orb15/configs).
"""

from tradebot.strategies.orb15.freqtrade import Orb15Strategy as _Orb15Strategy


class Orb15Strategy(_Orb15Strategy):
    pass
