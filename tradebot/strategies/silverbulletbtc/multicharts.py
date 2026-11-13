"""Silver Bullet 1.0 (BTC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SilverBulletBtcSignal"]


class SilverBulletBtcSignal(TradebotSignal):
    STRATEGY_KEY = "silverbulletbtc"
