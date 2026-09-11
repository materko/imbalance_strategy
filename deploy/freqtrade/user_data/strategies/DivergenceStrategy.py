"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/divergence/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: binance_btcusdt_15m z tradebot/strategies/divergence/configs/).
"""

from tradebot.strategies.divergence.freqtrade import DivergenceStrategy as _DivergenceStrategy


class DivergenceStrategy(_DivergenceStrategy):
    pass
