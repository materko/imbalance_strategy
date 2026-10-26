"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sdeurnet/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: eurusd_6e_5m z tradebot/strategies/sdeurnet/configs).
"""

from tradebot.strategies.sdeurnet.freqtrade import SdEurNetStrategy as _SdEurNetStrategy


class SdEurNetStrategy(_SdEurNetStrategy):
    pass
