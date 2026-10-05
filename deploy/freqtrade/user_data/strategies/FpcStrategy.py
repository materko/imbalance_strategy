"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/fpc/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_1m z tradebot/strategies/fpc/configs).
"""

from tradebot.strategies.fpc.freqtrade import FpcStrategy as _FpcStrategy


class FpcStrategy(_FpcStrategy):
    pass
