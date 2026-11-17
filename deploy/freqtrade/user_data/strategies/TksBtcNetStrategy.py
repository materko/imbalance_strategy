"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tksbtcnet/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_3m z tradebot/strategies/tksbtcnet/configs).
"""

from tradebot.strategies.tksbtcnet.freqtrade import TksBtcNetStrategy as _TksBtcNetStrategy


class TksBtcNetStrategy(_TksBtcNetStrategy):
    pass
