"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/rangebtc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_3m z tradebot/strategies/rangebtc/configs).
"""

from tradebot.strategies.rangebtc.freqtrade import RangeBtcStrategy as _RangeBtcStrategy


class RangeBtcStrategy(_RangeBtcStrategy):
    pass
