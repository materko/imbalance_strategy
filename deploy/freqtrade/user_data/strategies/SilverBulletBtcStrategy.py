"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/silverbulletbtc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_5m z tradebot/strategies/silverbulletbtc/configs).
"""

from tradebot.strategies.silverbulletbtc.freqtrade import SilverBulletBtcStrategy as _SilverBulletBtcStrategy


class SilverBulletBtcStrategy(_SilverBulletBtcStrategy):
    pass
