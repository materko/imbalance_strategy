"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `tradebot/strategies/demo_breakout/freqtrade.py` (nad generickou bazou
`tradebot/adapters/freqtrade/base.py`). Tento subor je len ukazovatel — resolver berie
do uvahy len triedy, ktorych `__module__` sa zhoduje s nazvom TOHTO suboru, preto ten
prazdny subclass.

Profil: TRADEBOT_PROFILE (default: binance_btcusdt_5m z tradebot/configs/demo_breakout).
"""

from tradebot.strategies.demo_breakout.freqtrade import DemoBreakoutStrategy as _DemoBreakoutStrategy


class DemoBreakoutStrategy(_DemoBreakoutStrategy):
    pass
