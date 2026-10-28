"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/m2mnq/freqtrade.py` (logika `tradebot/strategies/m2`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.m2mnq.freqtrade import M2MNQStrategy as _M2MNQStrategy


class M2MNQStrategy(_M2MNQStrategy):
    pass
