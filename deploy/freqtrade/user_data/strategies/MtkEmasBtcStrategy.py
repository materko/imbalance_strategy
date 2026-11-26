"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/mtkemasbtc/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: predvolený profil z tradebot/strategies/mtkemasbtc/configs).
"""

from tradebot.strategies.mtkemasbtc.freqtrade import MtkEmasBtcStrategy as _MtkEmasBtcStrategy


class MtkEmasBtcStrategy(_MtkEmasBtcStrategy):
    pass
