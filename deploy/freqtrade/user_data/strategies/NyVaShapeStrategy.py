"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/nyvashape/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_3m z tradebot/strategies/nyvashape/configs).
"""

from tradebot.strategies.nyvashape.freqtrade import NyVaShapeStrategy as _NyVaShapeStrategy


class NyVaShapeStrategy(_NyVaShapeStrategy):
    pass
