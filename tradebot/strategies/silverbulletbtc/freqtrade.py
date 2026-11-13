"""Silver Bullet 1.0 (BTC) vo Freqtrade — tie isté signály ako `SilverBulletStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SilverBulletBtcStrategy.py`.
"""

from __future__ import annotations

from ..silverbullet.freqtrade import SilverBulletStrategy

__all__ = ["SilverBulletBtcStrategy"]


class SilverBulletBtcStrategy(SilverBulletStrategy):
    STRATEGY_KEY = "silverbulletbtc"
    ENTRY_TAG_PREFIX = "silverbulletbtc:"

    timeframe = "5m"
