"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sigmamymnet/freqtrade.py` (logika `tradebot/strategies/fibo`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.sigmamymnet.freqtrade import SigmaMymNetStrategy as _SigmaMymNetStrategy


class SigmaMymNetStrategy(_SigmaMymNetStrategy):
    pass
