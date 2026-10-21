"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/fvgpolaritymgc/freqtrade.py` (logika `tradebot/strategies/fvgpolarity`).
Tento subor je len ukazovatel - Freqtrade resolver berie len triedu, ktorej `__module__` sa zhoduje s nazvom TOHTO suboru.
"""

from tradebot.strategies.fvgpolaritymgc.freqtrade import FvgPolarityMgcStrategy as _FvgPolarityMgcStrategy


class FvgPolarityMgcStrategy(_FvgPolarityMgcStrategy):
    pass
