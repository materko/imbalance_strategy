"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/scalp3mamgc/freqtrade.py` (logika `tradebot/strategies/scalp3ma`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.scalp3mamgc.freqtrade import Scalp3MaMgcStrategy as _Scalp3MaMgcStrategy


class Scalp3MaMgcStrategy(_Scalp3MaMgcStrategy):
    pass
