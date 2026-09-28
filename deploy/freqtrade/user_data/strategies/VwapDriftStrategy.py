"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/vwapdrift/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_5m z tradebot/strategies/vwapdrift/configs).
"""

from tradebot.strategies.vwapdrift.freqtrade import VwapDriftStrategy as _VwapDriftStrategy


class VwapDriftStrategy(_VwapDriftStrategy):
    pass
