"""MTK ZONE — SD zóny z 5m / 15m (klasické, vrchol volume profilu, nárast klasického objemu, min. počet potvrdení)
a vstupy limit na zónu / IBS / pin bar na grafe (3m / 2m).

Predloha: Pine „VP SD ZÓNY 50 — stratégia“ (10. 11. 2026, iCloud VOLUME-PROFILE — Pine nie je v repozitári).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, MtkZoneConfig, TradeDirection, VwapAnchor, VwapMode
from .engine import MtkZoneEngine
from .hyperopt import MtkZoneHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="mtkzone",
    title="MTK ZONE (SD zóny z volume)",
    config_cls=MtkZoneConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_3m",
    pine_path=None,
    pine_input_count=0,
    removed_inputs=REMOVED_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    sl_kind="sl_box",
    tp_kind="tp_box",
    kind_titles=KIND_TITLES,
    default_timeframe="3m",
    engine_factory=MtkZoneEngine,
    freqtrade_class="MtkZoneStrategy",
    multicharts_class="MtkZoneSignal",
    multicharts_template="MtkZone_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=MtkZoneHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "MtkZoneConfig", "MtkZoneEngine", "TradeDirection", "VwapMode", "VwapAnchor", "CONFIG_DIR"]
