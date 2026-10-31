"""LONDON LIQUIDITY IFVG 1.0 — sweep high / low seansy 13:00–19:00 NY a inverzný FVG.

Prepis Rust stratégie (`rq_sdk`, roboquant.dev Templates), ktorú poslal používateľ 29. 10. 2026; zadanie týždňa 31. 10. 2026.
Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, LliqConfig
from .engine import LliqEngine
from .hyperopt import LliqHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="lliq",
    title="LONDON LIQUIDITY IFVG 1.0",
    config_cls=LliqConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_5m",
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
    default_timeframe="5m",
    engine_factory=LliqEngine,
    freqtrade_class="LliqStrategy",
    multicharts_class="LliqSignal",
    multicharts_template="Lliq_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=LliqHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "LliqConfig", "LliqEngine", "CONFIG_DIR"]
