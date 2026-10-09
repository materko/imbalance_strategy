"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/voltbreak/freqtrade.py`. Tento subor je len ukazovatel.
Profil: TRADEBOT_PROFILE (default: mnq_databento_30m z tradebot/strategies/voltbreak/configs).
"""

from tradebot.strategies.voltbreak.freqtrade import VoltBreakStrategy as _VoltBreakStrategy


class VoltBreakStrategy(_VoltBreakStrategy):
    pass
