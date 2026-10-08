"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/percoco/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_1m z tradebot/strategies/percoco/configs).
"""

from tradebot.strategies.percoco.freqtrade import PercocoStrategy as _PercocoStrategy


class PercocoStrategy(_PercocoStrategy):
    pass
