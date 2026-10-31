"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sigma/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: mnq_databento_5m z tradebot/strategies/sigma/configs).
"""

from tradebot.strategies.sigma.freqtrade import SigmaStrategy as _SigmaStrategy


class SigmaStrategy(_SigmaStrategy):
    pass
