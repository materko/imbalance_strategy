"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/fvgpolarity/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_15m z tradebot/strategies/fvgpolarity/configs).
"""

from tradebot.strategies.fvgpolarity.freqtrade import FvgPolarityStrategy as _FvgPolarityStrategy


class FvgPolarityStrategy(_FvgPolarityStrategy):
    pass
