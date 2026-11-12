"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/wprmymnet/freqtrade.py` (logika `tradebot/strategies/fibo`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.wprmymnet.freqtrade import WprMymNetStrategy as _WprMymNetStrategy


class WprMymNetStrategy(_WprMymNetStrategy):
    pass
