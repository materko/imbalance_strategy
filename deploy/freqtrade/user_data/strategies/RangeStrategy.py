"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/range/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: nas100_dukascopy_3m z tradebot/strategies/range/configs).
"""

from tradebot.strategies.range.freqtrade import RangeStrategy as _RangeStrategy


class RangeStrategy(_RangeStrategy):
    pass
