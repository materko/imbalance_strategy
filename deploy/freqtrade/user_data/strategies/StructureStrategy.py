"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/structure/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: binance_btcusdt_5m z tradebot/strategies/structure/configs/).
"""

from tradebot.strategies.structure.freqtrade import StructureStrategy as _StructureStrategy


class StructureStrategy(_StructureStrategy):
    pass
