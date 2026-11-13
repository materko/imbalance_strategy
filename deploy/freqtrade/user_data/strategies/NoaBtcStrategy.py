"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/noabtc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_5m z tradebot/strategies/noabtc/configs).
"""

from tradebot.strategies.noabtc.freqtrade import NoaBtcStrategy as _NoaBtcStrategy


class NoaBtcStrategy(_NoaBtcStrategy):
    pass
