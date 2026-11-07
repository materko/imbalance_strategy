"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/va80/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_1m z tradebot/strategies/va80/configs).
"""

from tradebot.strategies.va80.freqtrade import Va80Strategy as _Va80Strategy


class Va80Strategy(_Va80Strategy):
    pass
