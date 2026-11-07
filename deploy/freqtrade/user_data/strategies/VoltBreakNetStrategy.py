"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/voltbreaknet/freqtrade.py` (logika `tradebot/strategies/fibo`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.voltbreaknet.freqtrade import VoltBreakNetStrategy as _VoltBreakNetStrategy


class VoltBreakNetStrategy(_VoltBreakNetStrategy):
    pass
