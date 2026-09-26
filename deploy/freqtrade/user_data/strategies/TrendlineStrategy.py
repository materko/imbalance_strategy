"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/trendlines/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: nas100_dukascopy_3m z tradebot/strategies/trendlines/configs).
"""

from tradebot.strategies.trendlines.freqtrade import TrendlineStrategy as _TrendlineStrategy


class TrendlineStrategy(_TrendlineStrategy):
    pass
