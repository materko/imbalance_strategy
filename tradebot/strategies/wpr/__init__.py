"""WILLIAMS %R LONG 1.0 — %R pod −90 long, výstup nad high predošlej sviečky alebo %R ≥ −30.

Prepis Rust stratégie (`rq_sdk`, roboquant.dev Templates), ktorú poslal používateľ 29. 10. 2026; zadanie týždňa 31. 10. 2026.
Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, WprConfig
from .engine import WprEngine
from .hyperopt import WprHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="wpr",
    title="WILLIAMS %R LONG 1.0",
    config_cls=WprConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_15m",
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
    default_timeframe="15m",
    engine_factory=WprEngine,
    freqtrade_class="WprStrategy",
    multicharts_class="WprSignal",
    multicharts_template="Wpr_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=WprHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "WprConfig", "WprEngine", "CONFIG_DIR"]
