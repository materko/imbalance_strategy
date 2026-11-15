"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/silverbulleteur/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: 6e_databento_5m z tradebot/strategies/silverbulleteur/configs).
"""

from tradebot.strategies.silverbulleteur.freqtrade import SilverBulletEurStrategy as _SilverBulletEurStrategy


class SilverBulletEurStrategy(_SilverBulletEurStrategy):
    pass
