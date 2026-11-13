"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/onbiasorbbtc/freqtrade.py`. Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten prazdny subclass.

Profil: TRADEBOT_PROFILE (default: btcusdt_binance_15m z tradebot/strategies/onbiasorbbtc/configs).
"""

from tradebot.strategies.onbiasorbbtc.freqtrade import OnBiasOrbBtcStrategy as _OnBiasOrbBtcStrategy


class OnBiasOrbBtcStrategy(_OnBiasOrbBtcStrategy):
    pass
