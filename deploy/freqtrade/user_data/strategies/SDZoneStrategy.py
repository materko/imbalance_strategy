"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sdzone/freqtrade.py`. Tento subor je len
ukazovatel — resolver berie do uvahy len triedy, ktorych `__module__` sa zhoduje
s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: xau_dukascopy_15m z tradebot/strategies/sdzone/configs).
"""

from tradebot.strategies.sdzone.freqtrade import SDZoneStrategy as _SDZoneStrategy


class SDZoneStrategy(_SDZoneStrategy):
    pass
