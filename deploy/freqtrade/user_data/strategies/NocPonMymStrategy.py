"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/nocponmym/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mym_databento_5m z tradebot/strategies/nocponmym/configs).
"""

from tradebot.strategies.nocponmym.freqtrade import NocPonMymStrategy as _NocPonMymStrategy


class NocPonMymStrategy(_NocPonMymStrategy):
    pass
