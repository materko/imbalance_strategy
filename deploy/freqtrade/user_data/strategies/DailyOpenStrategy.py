"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/dailyopen/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_60m z tradebot/strategies/dailyopen/configs).
"""

from tradebot.strategies.dailyopen.freqtrade import DailyOpenStrategy as _DailyOpenStrategy


class DailyOpenStrategy(_DailyOpenStrategy):
    pass
