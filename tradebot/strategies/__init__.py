"""Registry stratégií — jediné miesto, ktoré pozná všetky stratégie menom.

Pridanie stratégie: balík `tradebot/strategies/<key>/` so `SPEC`, riadok sem.
Registry je obyčajný dict s explicitnými importmi — bez entry-pointov a mágie.
"""

from __future__ import annotations

from .asiasweep import SPEC as ASIASWEEP_SPEC
from .base import StrategySpec
from .breakout import SPEC as BREAKOUT_SPEC
from .crt import SPEC as CRT_SPEC
from .dailyopen import SPEC as DAILYOPEN_SPEC
from .noa import SPEC as NOA_SPEC
from .tks import SPEC as TKS_SPEC
from .tksnet import SPEC as TKSNET_SPEC
from .tksneteod import SPEC as TKSNETEOD_SPEC
from .nocpon import SPEC as NOCPON_SPEC
from .demo_breakout import SPEC as DEMO_SPEC
from .divergence import SPEC as DIVERGENCE_SPEC
from .fvgpolarity import SPEC as FVGPOLARITY_SPEC
from .fvgpolaritymgc import SPEC as FVGPOLARITYMGC_SPEC
from .fibo import SPEC as FIBO_SPEC
from .fpc import SPEC as FPC_SPEC
from .gap import SPEC as GAP_SPEC
from .ibs import SPEC as IBS_SPEC
from .ibsnet import SPEC as IBSNET_SPEC
from .ibsentry import SPEC as IBSENTRY_SPEC
from .ibsentrymgc import SPEC as IBSENTRYMGC_SPEC
from .ibsentrynet import SPEC as IBSENTRYNET_SPEC
from .ibsentryneteod import SPEC as IBSENTRYNETEOD_SPEC
from .ibsfvg import SPEC as IBSFVG_SPEC
from .ibszones import SPEC as IBSZONES_SPEC
from .jss import SPEC as JSS_SPEC
from .liquidity import SPEC as LIQUIDITY_SPEC
from .mag7 import SPEC as MAG7_SPEC
from .onbiasorb import SPEC as ONBIASORB_SPEC
from .orb import SPEC as ORB_SPEC
from .orbnet import SPEC as ORBNET_SPEC
from .range import SPEC as RANGE_SPEC
from .scalp3ma import SPEC as SCALP3MA_SPEC
from .sdzone import SPEC as SDZONE_SPEC
from .structure import SPEC as STRUCTURE_SPEC
from .percoco import SPEC as PERCOCO_SPEC
from .svp import SPEC as SVP_SPEC
from .sweepengulf import SPEC as SWEEPENGULF_SPEC
from .sweepfvg import SPEC as SWEEPFVG_SPEC
from .silverbullet import SPEC as SILVERBULLET_SPEC
from .noanet import SPEC as NOANET_SPEC
from .noaneteod import SPEC as NOANETEOD_SPEC
from .trendlines import SPEC as TRENDLINES_SPEC
from .varev import SPEC as VAREV_SPEC
from .voltbreak import SPEC as VOLTBREAK_SPEC
from .vwapadx import SPEC as VWAPADX_SPEC
from .vwapadxnet import SPEC as VWAPADXNET_SPEC
from .vwapadxneteod import SPEC as VWAPADXNETEOD_SPEC
from .vwapdrift import SPEC as VWAPDRIFT_SPEC
from .vwapop import SPEC as VWAPOP_SPEC
from .vwaporb import SPEC as VWAPORB_SPEC
from .vwaporbnet import SPEC as VWAPORBNET_SPEC
from .vwaporbneteod import SPEC as VWAPORBNETEOD_SPEC

STRATEGIES: dict[str, StrategySpec] = {
    IBS_SPEC.key: IBS_SPEC,
    IBSNET_SPEC.key: IBSNET_SPEC,
    IBSZONES_SPEC.key: IBSZONES_SPEC,
    IBSENTRY_SPEC.key: IBSENTRY_SPEC,
    IBSENTRYMGC_SPEC.key: IBSENTRYMGC_SPEC,
    IBSENTRYNET_SPEC.key: IBSENTRYNET_SPEC,
    IBSENTRYNETEOD_SPEC.key: IBSENTRYNETEOD_SPEC,
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
    TRENDLINES_SPEC.key: TRENDLINES_SPEC,
    LIQUIDITY_SPEC.key: LIQUIDITY_SPEC,
    VWAPDRIFT_SPEC.key: VWAPDRIFT_SPEC,
    VWAPADX_SPEC.key: VWAPADX_SPEC,
    VWAPADXNET_SPEC.key: VWAPADXNET_SPEC,
    VWAPADXNETEOD_SPEC.key: VWAPADXNETEOD_SPEC,
    VOLTBREAK_SPEC.key: VOLTBREAK_SPEC,
    ONBIASORB_SPEC.key: ONBIASORB_SPEC,
    VWAPOP_SPEC.key: VWAPOP_SPEC,
    VWAPORB_SPEC.key: VWAPORB_SPEC,
    VWAPORBNET_SPEC.key: VWAPORBNET_SPEC,
    VWAPORBNETEOD_SPEC.key: VWAPORBNETEOD_SPEC,
    JSS_SPEC.key: JSS_SPEC,
    CRT_SPEC.key: CRT_SPEC,
    SCALP3MA_SPEC.key: SCALP3MA_SPEC,
    FIBO_SPEC.key: FIBO_SPEC,
    SVP_SPEC.key: SVP_SPEC,
    PERCOCO_SPEC.key: PERCOCO_SPEC,
    FVGPOLARITY_SPEC.key: FVGPOLARITY_SPEC,
    FVGPOLARITYMGC_SPEC.key: FVGPOLARITYMGC_SPEC,
    FPC_SPEC.key: FPC_SPEC,
    MAG7_SPEC.key: MAG7_SPEC,
    ASIASWEEP_SPEC.key: ASIASWEEP_SPEC,
    DAILYOPEN_SPEC.key: DAILYOPEN_SPEC,
    NOA_SPEC.key: NOA_SPEC,
    TKS_SPEC.key: TKS_SPEC,
    TKSNET_SPEC.key: TKSNET_SPEC,
    TKSNETEOD_SPEC.key: TKSNETEOD_SPEC,
    NOCPON_SPEC.key: NOCPON_SPEC,
    SWEEPFVG_SPEC.key: SWEEPFVG_SPEC,
    SILVERBULLET_SPEC.key: SILVERBULLET_SPEC,
    NOANET_SPEC.key: NOANET_SPEC,
    NOANETEOD_SPEC.key: NOANETEOD_SPEC,
    SWEEPENGULF_SPEC.key: SWEEPENGULF_SPEC,
    VAREV_SPEC.key: VAREV_SPEC,
}

#: Staré kľúče -> dnešné. História behov, profily a odkazy z minulosti sa nemenia na disku;
#: každé čítanie kľúča ide cez `canonical_key`, takže staré záznamy patria k premenovanej stratégii.
ALIASES: dict[str, str] = {
    "ibsninja": IBSNET_SPEC.key,    # IBSNinja -> IBSNet (25. 9. 2026: .NET jadro nie je len pre NinjaTrader)
    "orbninja": ORBNET_SPEC.key,    # ORBNinja -> ORBNet
    "trendline": TRENDLINES_SPEC.key,  # prvé skúšobné behy 26. 9. 2026 pred premenovaním na Trendlines
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
