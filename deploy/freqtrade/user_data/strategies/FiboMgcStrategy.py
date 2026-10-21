"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/fibomgc/freqtrade.py` (logika `tradebot/strategies/fibo`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.fibomgc.freqtrade import FiboMgcStrategy as _FiboMgcStrategy


class FiboMgcStrategy(_FiboMgcStrategy):
    pass
