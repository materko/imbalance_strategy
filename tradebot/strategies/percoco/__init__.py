"""Craig Percoco 1.0 — štruktúra trhu a momentum: 15m trend a FVG, 1m CHoCH + FVG, limitka na stred FVG.

Podľa videa Craiga Percoca „This Boring Strategy Made Me $53,478 In A Month" (8. 10. 2026).
Stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, PercocoConfig, TradeDirection
from .engine import PercocoEngine
from .hyperopt import PercocoHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="percoco",
    title="Craig Percoco 1.0",
    config_cls=PercocoConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_1m",
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
    default_timeframe="1m",
    engine_factory=PercocoEngine,
    freqtrade_class="PercocoStrategy",
    multicharts_class="PercocoSignal",
    multicharts_template="Percoco_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=PercocoHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "PercocoConfig", "PercocoEngine", "TradeDirection", "CONFIG_DIR"]
