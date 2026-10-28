"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/m2eur/freqtrade.py` (logika `tradebot/strategies/m2`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.m2eur.freqtrade import M2EURStrategy as _M2EURStrategy


class M2EURStrategy(_M2EURStrategy):
    pass
