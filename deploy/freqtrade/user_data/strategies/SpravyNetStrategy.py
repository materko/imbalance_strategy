"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/spravynet/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mgc_databento_5m z tradebot/strategies/spravynet/configs).
"""

from tradebot.strategies.spravynet.freqtrade import SpravyNetStrategy as _SpravyNetStrategy


class SpravyNetStrategy(_SpravyNetStrategy):
    pass
