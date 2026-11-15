"""Silver Bullet 1.0 (6E) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SilverBulletEurSignal"]


class SilverBulletEurSignal(TradebotSignal):
    STRATEGY_KEY = "silverbulleteur"
