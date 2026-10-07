"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/asiasweep/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: eurusd_dukascopy_5m z tradebot/strategies/asiasweep/configs).
"""

from tradebot.strategies.asiasweep.freqtrade import AsiaSweepStrategy as _AsiaSweepStrategy


class AsiaSweepStrategy(_AsiaSweepStrategy):
    pass
