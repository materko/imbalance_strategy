"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/vwapadx/freqtrade.py`. Tento subor je len ukazovatel —
resolver berie do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru.

Profil: TRADEBOT_PROFILE (default: mnq_databento_1m z tradebot/strategies/vwapadx/configs).
"""

from tradebot.strategies.vwapadx.freqtrade import VwapAdxStrategy as _VwapAdxStrategy


class VwapAdxStrategy(_VwapAdxStrategy):
    pass
