"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/mtkemasmym/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: predvolený profil z tradebot/strategies/mtkemasmym/configs).
"""

from tradebot.strategies.mtkemasmym.freqtrade import MtkEmasMymStrategy as _MtkEmasMymStrategy


class MtkEmasMymStrategy(_MtkEmasMymStrategy):
    pass
