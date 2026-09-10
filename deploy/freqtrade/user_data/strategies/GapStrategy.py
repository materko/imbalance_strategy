"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/gap/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel.

Profil: TRADEBOT_PROFILE (default: nas100_dukascopy_5m z tradebot/strategies/gap/configs).
"""

from tradebot.strategies.gap.freqtrade import GapStrategy as _GapStrategy


class GapStrategy(_GapStrategy):
    pass
