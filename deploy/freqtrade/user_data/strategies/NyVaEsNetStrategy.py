"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/nyvaesnet/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1 z tradebot/strategies/nyvaesnet/configs).
"""

from tradebot.strategies.nyvaesnet.freqtrade import NyVaEsNetStrategy as _NyVaEsNetStrategy


class NyVaEsNetStrategy(_NyVaEsNetStrategy):
    pass
