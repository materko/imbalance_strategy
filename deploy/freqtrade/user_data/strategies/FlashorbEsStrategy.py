"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/flashorbes/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_15m z tradebot/strategies/flashorbes/configs).
"""

from tradebot.strategies.flashorbes.freqtrade import FlashorbEsStrategy as _FlashorbEsStrategy


class FlashorbEsStrategy(_FlashorbEsStrategy):
    pass
