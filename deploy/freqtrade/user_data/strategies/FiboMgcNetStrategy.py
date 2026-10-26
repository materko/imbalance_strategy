"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/fibomgcnet/freqtrade.py` (logika `tradebot/strategies/fibo`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.fibomgcnet.freqtrade import FiboMgcNetStrategy as _FiboMgcNetStrategy


class FiboMgcNetStrategy(_FiboMgcNetStrategy):
    pass
