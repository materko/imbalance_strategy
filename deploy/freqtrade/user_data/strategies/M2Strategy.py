"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/m2/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: es_databento_1m z tradebot/strategies/m2/configs).
"""

from tradebot.strategies.m2.freqtrade import M2Strategy as _M2Strategy


class M2Strategy(_M2Strategy):
    pass
