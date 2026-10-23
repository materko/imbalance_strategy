"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/nyvaes/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_3m z tradebot/strategies/nyvaes/configs).
"""

from tradebot.strategies.nyvaes.freqtrade import NyVaEsStrategy as _NyVaEsStrategy


class NyVaEsStrategy(_NyVaEsStrategy):
    pass
