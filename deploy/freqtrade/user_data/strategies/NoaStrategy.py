"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/noa/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_5m z tradebot/strategies/noa/configs).
"""

from tradebot.strategies.noa.freqtrade import NoaStrategy as _NoaStrategy


class NoaStrategy(_NoaStrategy):
    pass
