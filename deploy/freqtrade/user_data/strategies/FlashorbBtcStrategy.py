"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/flashorbbtc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_15m z tradebot/strategies/flashorbbtc/configs).
"""

from tradebot.strategies.flashorbbtc.freqtrade import FlashorbBtcStrategy as _FlashorbBtcStrategy


class FlashorbBtcStrategy(_FlashorbBtcStrategy):
    pass
