"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sweepengulfeur/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: 6e_databento_4h z tradebot/strategies/sweepengulfeur/configs).
"""

from tradebot.strategies.sweepengulfeur.freqtrade import SweepEngulfEurStrategy as _SweepEngulfEurStrategy


class SweepEngulfEurStrategy(_SweepEngulfEurStrategy):
    pass
