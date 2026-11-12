"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sweepengulfmym/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_4h z tradebot/strategies/sweepengulfmym/configs).
"""

from tradebot.strategies.sweepengulfmym.freqtrade import SweepEngulfMymStrategy as _SweepEngulfMymStrategy


class SweepEngulfMymStrategy(_SweepEngulfMymStrategy):
    pass
