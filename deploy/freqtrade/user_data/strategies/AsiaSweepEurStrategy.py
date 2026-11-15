"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/asiasweepeur/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: 6e_databento_5m z tradebot/strategies/asiasweepeur/configs).
"""

from tradebot.strategies.asiasweepeur.freqtrade import AsiaSweepEurStrategy as _AsiaSweepEurStrategy


class AsiaSweepEurStrategy(_AsiaSweepEurStrategy):
    pass
