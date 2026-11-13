"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/noabtcnet/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_5m z tradebot/strategies/noabtcnet/configs).
"""

from tradebot.strategies.noabtcnet.freqtrade import NoaBtcNetStrategy as _NoaBtcNetStrategy


class NoaBtcNetStrategy(_NoaBtcNetStrategy):
    pass
