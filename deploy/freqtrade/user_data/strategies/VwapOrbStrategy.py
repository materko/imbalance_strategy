"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/vwaporb/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_5m z tradebot/strategies/vwaporb/configs).
"""

from tradebot.strategies.vwaporb.freqtrade import VwapOrbStrategy as _VwapOrbStrategy


class VwapOrbStrategy(_VwapOrbStrategy):
    pass
