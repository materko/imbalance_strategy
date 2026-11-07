"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sigmamgcnet/freqtrade.py` (logika `tradebot/strategies/fibo`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.sigmamgcnet.freqtrade import SigmaMgcNetStrategy as _SigmaMgcNetStrategy


class SigmaMgcNetStrategy(_SigmaMgcNetStrategy):
    pass
