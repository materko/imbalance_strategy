"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/flashorb/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_15m z tradebot/strategies/flashorb/configs).
"""

from tradebot.strategies.flashorb.freqtrade import FlashorbStrategy as _FlashorbStrategy


class FlashorbStrategy(_FlashorbStrategy):
    pass
