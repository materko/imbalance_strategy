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
from .nyvaes import SPEC as NYVAES_SPEC
from .nyvaesnet import SPEC as NYVAESNET_SPEC
from .demo_breakout import SPEC as DEMO_SPEC
from .divergence import SPEC as DIVERGENCE_SPEC
from .fvgpolarity import SPEC as FVGPOLARITY_SPEC
from .fvgpolaritymgc import SPEC as FVGPOLARITYMGC_SPEC
from .fibo import SPEC as FIBO_SPEC
from .fibomgc import SPEC as FIBOMGC_SPEC
from .fibomgcnet import SPEC as FIBOMGCNET_SPEC
from .sdeur import SPEC as SDEUR_SPEC
from .nb import SPEC as NB_SPEC
from .m2 import SPEC as M2_SPEC
from .m2mnq import SPEC as M2MNQ_SPEC
from .m2eur import SPEC as M2EUR_SPEC
from .m2mgc import SPEC as M2MGC_SPEC
from .ivb import SPEC as IVB_SPEC
from .wprnet import SPEC as WPRNET_SPEC
from .voltbreaknet import SPEC as VOLTBREAKNET_SPEC
from .sigmamgcnet import SPEC as SIGMAMGCNET_SPEC
from .sigmanet import SPEC as SIGMANET_SPEC
from .orb15 import SPEC as ORB15_SPEC
from .orb15es import SPEC as ORB15ES_SPEC
from .orb15mgc import SPEC as ORB15MGC_SPEC
from .tmr import SPEC as TMR_SPEC
from .tmres import SPEC as TMRES_SPEC
from .tmrmgc import SPEC as TMRMGC_SPEC
from .wpr import SPEC as WPR_SPEC
from .wpres import SPEC as WPRES_SPEC
from .wprmgc import SPEC as WPRMGC_SPEC
from .flashorb import SPEC as FLASHORB_SPEC
from .flashorbes import SPEC as FLASHORBES_SPEC
from .flashorbmgc import SPEC as FLASHORBMGC_SPEC
from .sigma import SPEC as SIGMA_SPEC
from .sigmaes import SPEC as SIGMAES_SPEC
from .sigmamgc import SPEC as SIGMAMGC_SPEC
from .nqprec import SPEC as NQPREC_SPEC
from .nqpreces import SPEC as NQPRECES_SPEC
from .nqprecmgc import SPEC as NQPRECMGC_SPEC
from .lliq import SPEC as LLIQ_SPEC
from .lliqes import SPEC as LLIQES_SPEC
from .lliqmgc import SPEC as LLIQMGC_SPEC
from .ivbes import SPEC as IVBES_SPEC
from .ivbmgc import SPEC as IVBMGC_SPEC
from .spravy import SPEC as SPRAVY_SPEC
from .spravynet import SPEC as SPRAVYNET_SPEC
from .sdeurnet import SPEC as SDEURNET_SPEC
from .fpc import SPEC as FPC_SPEC
from .gap import SPEC as GAP_SPEC
from .ibs import SPEC as IBS_SPEC
from .ibsnet import SPEC as IBSNET_SPEC
from .ibsentry import SPEC as IBSENTRY_SPEC
from .ibsentrymgc import SPEC as IBSENTRYMGC_SPEC
from .ibsentryes import SPEC as IBSENTRYES_SPEC
from .ibsentryesnet import SPEC as IBSENTRYESNET_SPEC
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
from .scalp3mamgc import SPEC as SCALP3MAMGC_SPEC
from .sdzone import SPEC as SDZONE_SPEC
from .structure import SPEC as STRUCTURE_SPEC
from .percoco import SPEC as PERCOCO_SPEC
from .svp import SPEC as SVP_SPEC
from .sweepengulf import SPEC as SWEEPENGULF_SPEC
from .mtkzone import SPEC as MTKZONE_SPEC
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

def _registry(specs: tuple[StrategySpec, ...]) -> dict[str, StrategySpec]:
    """Slovník kľúč → stratégia; dva balíky s tým istým kľúčom sú chyba, nie tiché prepísanie.

    Literál slovníka by druhý výskyt kľúča potichu nechal vyhrať a prvá stratégia by z registry zmizla
    (audit M-CORE-9) — skopírovaný balík so zabudnutým `key` sa tak prejaví hneď pri importe.
    """
    out: dict[str, StrategySpec] = {}
    for spec in specs:
        if spec.key in out:
            raise ValueError(f"kľúč stratégie {spec.key!r} je v registry dvakrát: "
                             f"{out[spec.key].config_cls.__module__} a {spec.config_cls.__module__}")
        out[spec.key] = spec
    return out


STRATEGIES: dict[str, StrategySpec] = _registry((
    IBS_SPEC,
    IBSNET_SPEC,
    IBSZONES_SPEC,
    IBSENTRY_SPEC,
    IBSENTRYMGC_SPEC,
    IBSENTRYES_SPEC,
    IBSENTRYESNET_SPEC,
    IBSENTRYNET_SPEC,
    IBSENTRYNETEOD_SPEC,
    IBSFVG_SPEC,
    STRUCTURE_SPEC,
    DEMO_SPEC,
    ORB_SPEC,
    ORBNET_SPEC,
    GAP_SPEC,
    RANGE_SPEC,
    SDZONE_SPEC,
    BREAKOUT_SPEC,
    DIVERGENCE_SPEC,
    TRENDLINES_SPEC,
    LIQUIDITY_SPEC,
    VWAPDRIFT_SPEC,
    VWAPADX_SPEC,
    VWAPADXNET_SPEC,
    VWAPADXNETEOD_SPEC,
    VOLTBREAK_SPEC,
    ONBIASORB_SPEC,
    VWAPOP_SPEC,
    VWAPORB_SPEC,
    VWAPORBNET_SPEC,
    VWAPORBNETEOD_SPEC,
    JSS_SPEC,
    CRT_SPEC,
    SCALP3MA_SPEC,
    SCALP3MAMGC_SPEC,
    FIBO_SPEC,
    FIBOMGC_SPEC,
    FIBOMGCNET_SPEC,
    SVP_SPEC,
    PERCOCO_SPEC,
    FVGPOLARITY_SPEC,
    FVGPOLARITYMGC_SPEC,
    FPC_SPEC,
    MAG7_SPEC,
    ASIASWEEP_SPEC,
    DAILYOPEN_SPEC,
    NOA_SPEC,
    TKS_SPEC,
    TKSNET_SPEC,
    TKSNETEOD_SPEC,
    NOCPON_SPEC,
    NYVAES_SPEC,
    NYVAESNET_SPEC,
    SDEUR_SPEC,
    SDEURNET_SPEC,
    NB_SPEC,
    M2_SPEC,
    M2MNQ_SPEC,
    M2EUR_SPEC,
    M2MGC_SPEC,
    IVB_SPEC,
    WPRNET_SPEC,
    VOLTBREAKNET_SPEC,
    SIGMAMGCNET_SPEC,
    SIGMANET_SPEC,
    ORB15_SPEC,
    ORB15ES_SPEC,
    ORB15MGC_SPEC,
    TMR_SPEC,
    TMRES_SPEC,
    TMRMGC_SPEC,
    WPR_SPEC,
    WPRES_SPEC,
    WPRMGC_SPEC,
    FLASHORB_SPEC,
    FLASHORBES_SPEC,
    FLASHORBMGC_SPEC,
    SIGMA_SPEC,
    SIGMAES_SPEC,
    SIGMAMGC_SPEC,
    NQPREC_SPEC,
    NQPRECES_SPEC,
    NQPRECMGC_SPEC,
    LLIQ_SPEC,
    LLIQES_SPEC,
    LLIQMGC_SPEC,
    IVBES_SPEC,
    IVBMGC_SPEC,
    SPRAVY_SPEC,
    SPRAVYNET_SPEC,
    SWEEPFVG_SPEC,
    SILVERBULLET_SPEC,
    NOANET_SPEC,
    NOANETEOD_SPEC,
    SWEEPENGULF_SPEC,
    MTKZONE_SPEC,
    VAREV_SPEC,
))

#: Staré kľúče -> dnešné. História behov, profily a odkazy z minulosti sa nemenia na disku;
#: každé čítanie kľúča ide cez `canonical_key`, takže staré záznamy patria k premenovanej stratégii.
ALIASES: dict[str, str] = {
    "ibsninja": IBSNET_SPEC.key,    # IBSNinja -> IBSNet (25. 9. 2026: .NET jadro nie je len pre NinjaTrader)
    "orbninja": ORBNET_SPEC.key,    # ORBNinja -> ORBNet
    "trendline": TRENDLINES_SPEC.key,  # prvé skúšobné behy 26. 9. 2026 pred premenovaním na Trendlines
}

_kolizie = sorted(set(ALIASES) & set(STRATEGIES))
if _kolizie:  # starý názov nesmie zatieniť živú stratégiu (`canonical_key` by ju presmeroval inam)
    raise ValueError(f"alias je zároveň kľúč stratégie: {_kolizie}")

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
