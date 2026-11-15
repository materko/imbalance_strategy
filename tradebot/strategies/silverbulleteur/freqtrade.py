"""Silver Bullet 1.0 (6E) vo Freqtrade — tie isté signály ako `SilverBulletStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SilverBulletEurStrategy.py`.
"""

from __future__ import annotations

from ..silverbullet.freqtrade import SilverBulletStrategy

__all__ = ["SilverBulletEurStrategy"]


class SilverBulletEurStrategy(SilverBulletStrategy):
    STRATEGY_KEY = "silverbulleteur"
    ENTRY_TAG_PREFIX = "silverbulleteur:"

    timeframe = "5m"
