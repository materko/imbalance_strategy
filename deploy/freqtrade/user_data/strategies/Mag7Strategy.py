"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/mag7/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_15m z tradebot/strategies/mag7/configs).
"""

from tradebot.strategies.mag7.freqtrade import Mag7Strategy as _Mag7Strategy


class Mag7Strategy(_Mag7Strategy):
    pass
