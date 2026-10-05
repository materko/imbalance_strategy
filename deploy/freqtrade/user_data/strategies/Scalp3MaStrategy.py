"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/scalp3ma/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: nas100_dukascopy_3m z tradebot/strategies/scalp3ma/configs).
"""

from tradebot.strategies.scalp3ma.freqtrade import Scalp3MaStrategy as _Scalp3MaStrategy


class Scalp3MaStrategy(_Scalp3MaStrategy):
    pass
