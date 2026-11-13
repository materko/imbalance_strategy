"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/dailyopenbtc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_1h z tradebot/strategies/dailyopenbtc/configs).
"""

from tradebot.strategies.dailyopenbtc.freqtrade import DailyOpenBtcStrategy as _DailyOpenBtcStrategy


class DailyOpenBtcStrategy(_DailyOpenBtcStrategy):
    pass
