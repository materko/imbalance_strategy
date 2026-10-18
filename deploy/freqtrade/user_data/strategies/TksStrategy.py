"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tks/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_3m z tradebot/strategies/tks/configs).
"""

from tradebot.strategies.tks.freqtrade import TksStrategy as _TksStrategy


class TksStrategy(_TksStrategy):
    pass
