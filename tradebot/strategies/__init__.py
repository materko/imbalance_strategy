"""Registry stratégií — jediné miesto, ktoré pozná všetky stratégie menom.

Pridanie stratégie: balík `tradebot/strategies/<key>/` so `SPEC`, riadok sem.
Registry je obyčajný dict s explicitnými importmi — bez entry-pointov a mágie.
"""

from __future__ import annotations

from .base import StrategySpec
from .breakout import SPEC as BREAKOUT_SPEC
from .demo_breakout import SPEC as DEMO_SPEC
from .divergence import SPEC as DIVERGENCE_SPEC
from .gap import SPEC as GAP_SPEC
from .ibs import SPEC as IBS_SPEC
from .ibsnet import SPEC as IBSNET_SPEC
from .ibsentry import SPEC as IBSENTRY_SPEC
from .ibsfvg import SPEC as IBSFVG_SPEC
from .ibszones import SPEC as IBSZONES_SPEC
from .orb import SPEC as ORB_SPEC
from .orbnet import SPEC as ORBNET_SPEC
from .range import SPEC as RANGE_SPEC
from .sdzone import SPEC as SDZONE_SPEC
from .structure import SPEC as STRUCTURE_SPEC

STRATEGIES: dict[str, StrategySpec] = {
    IBS_SPEC.key: IBS_SPEC,
    IBSNET_SPEC.key: IBSNET_SPEC,
    IBSZONES_SPEC.key: IBSZONES_SPEC,
    IBSENTRY_SPEC.key: IBSENTRY_SPEC,
    IBSFVG_SPEC.key: IBSFVG_SPEC,
    STRUCTURE_SPEC.key: STRUCTURE_SPEC,
    DEMO_SPEC.key: DEMO_SPEC,
    ORB_SPEC.key: ORB_SPEC,
    ORBNET_SPEC.key: ORBNET_SPEC,
    GAP_SPEC.key: GAP_SPEC,
    RANGE_SPEC.key: RANGE_SPEC,
    SDZONE_SPEC.key: SDZONE_SPEC,
    BREAKOUT_SPEC.key: BREAKOUT_SPEC,
    DIVERGENCE_SPEC.key: DIVERGENCE_SPEC,
}

#: Staré kľúče -> dnešné. História behov, profily a odkazy z minulosti sa nemenia na disku;
#: každé čítanie kľúča ide cez `canonical_key`, takže staré záznamy patria k premenovanej stratégii.
ALIASES: dict[str, str] = {
    "ibsninja": IBSNET_SPEC.key,    # IBSNinja -> IBSNet (25. 9. 2026: .NET jadro nie je len pre NinjaTrader)
    "orbninja": ORBNET_SPEC.key,    # ORBNinja -> ORBNet
}

__all__ = ["ALIASES", "STRATEGIES", "StrategySpec", "canonical_key", "get_spec", "spec_for_config"]


def canonical_key(key: str | None) -> str | None:
    """Dnešný kľúč stratégie aj pre starý názov; neznámy kľúč vráti nezmenený."""
    return ALIASES.get(key, key) if key else key


def spec_for_config(cfg) -> StrategySpec:
    """Stratégia podľa triedy configu — adaptéry tak nepotrebujú kľúč navyše."""
    # najprv presná trieda: config stratégie, ktorá dedí z inej (IBSNet z IBS, ORBNet z ORB), patrí jej
    for spec in STRATEGIES.values():
        if type(cfg) is spec.config_cls:
            return spec
    for spec in STRATEGIES.values():
        if isinstance(cfg, spec.config_cls):
            return spec
    raise KeyError(f"config {type(cfg).__name__} nepatrí žiadnej registrovanej stratégii")


def get_spec(key: str) -> StrategySpec:
    try:
        return STRATEGIES[canonical_key(key)]
    except KeyError:
        raise KeyError(f"neznáma stratégia {key!r}; známe: {sorted(STRATEGIES)}") from None
