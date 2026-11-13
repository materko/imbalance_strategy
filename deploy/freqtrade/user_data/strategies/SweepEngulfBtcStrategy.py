"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/sweepengulfbtc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_4h z tradebot/strategies/sweepengulfbtc/configs).
"""

from tradebot.strategies.sweepengulfbtc.freqtrade import SweepEngulfBtcStrategy as _SweepEngulfBtcStrategy


class SweepEngulfBtcStrategy(_SweepEngulfBtcStrategy):
    pass
