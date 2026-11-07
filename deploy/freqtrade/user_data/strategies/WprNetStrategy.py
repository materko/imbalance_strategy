"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/wprnet/freqtrade.py` (logika `tradebot/strategies/fibo`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.wprnet.freqtrade import WprNetStrategy as _WprNetStrategy


class WprNetStrategy(_WprNetStrategy):
    pass
