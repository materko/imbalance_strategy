"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/tmrbtc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_15m z tradebot/strategies/tmrbtc/configs).
"""

from tradebot.strategies.tmrbtc.freqtrade import TmrBtcStrategy as _TmrBtcStrategy


class TmrBtcStrategy(_TmrBtcStrategy):
    pass
