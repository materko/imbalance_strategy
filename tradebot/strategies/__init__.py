"""Registry stratégií — jediné miesto, ktoré pozná všetky stratégie menom.

Pridanie stratégie: balík `tradebot/strategies/<key>/` so `SPEC`, riadok sem.
Registry je obyčajný dict s explicitnými importmi — bez entry-pointov a mágie.
"""

from __future__ import annotations

from .base import StrategySpec
from .ibs import SPEC as IBS_SPEC

STRATEGIES: dict[str, StrategySpec] = {
    IBS_SPEC.key: IBS_SPEC,
}

__all__ = ["STRATEGIES", "StrategySpec", "get_spec"]


def get_spec(key: str) -> StrategySpec:
    try:
        return STRATEGIES[key]
    except KeyError:
        raise KeyError(f"neznáma stratégia {key!r}; známe: {sorted(STRATEGIES)}") from None
