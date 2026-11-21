"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/spravy/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: 6e_databento_5m z tradebot/strategies/spravyeur/configs).
"""

from tradebot.strategies.spravyeur.freqtrade import SpravyEurStrategy as _SpravyEurStrategy


class SpravyEurStrategy(_SpravyEurStrategy):
    pass
