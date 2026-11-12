"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/wprmym/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_15m z tradebot/strategies/wprmym/configs).
"""

from tradebot.strategies.wprmym.freqtrade import WprMymStrategy as _WprMymStrategy


class WprMymStrategy(_WprMymStrategy):
    pass
