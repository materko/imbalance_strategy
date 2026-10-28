"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/m2mgc/freqtrade.py` (logika `tradebot/strategies/m2`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.m2mgc.freqtrade import M2MGCStrategy as _M2MGCStrategy


class M2MGCStrategy(_M2MGCStrategy):
    pass
