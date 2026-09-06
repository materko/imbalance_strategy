"""Registry stratégií — jediné miesto, ktoré pozná všetky stratégie menom.

Pridanie stratégie: balík `tradebot/strategies/<key>/` so `SPEC`, riadok sem.
Registry je obyčajný dict s explicitnými importmi — bez entry-pointov a mágie.
"""

from __future__ import annotations

from .base import StrategySpec
from .demo_breakout import SPEC as DEMO_SPEC
from .ibs import SPEC as IBS_SPEC

STRATEGIES: dict[str, StrategySpec] = {
    IBS_SPEC.key: IBS_SPEC,
    DEMO_SPEC.key: DEMO_SPEC,
}

__all__ = ["STRATEGIES", "StrategySpec", "get_spec", "spec_for_config"]


def spec_for_config(cfg) -> StrategySpec:
    """Stratégia podľa triedy configu — adaptéry tak nepotrebujú kľúč navyše."""
    for spec in STRATEGIES.values():
        if isinstance(cfg, spec.config_cls):
            return spec
    raise KeyError(f"config {type(cfg).__name__} nepatrí žiadnej registrovanej stratégii")


def get_spec(key: str) -> StrategySpec:
    try:
        return STRATEGIES[key]
    except KeyError:
        raise KeyError(f"neznáma stratégia {key!r}; známe: {sorted(STRATEGIES)}") from None
