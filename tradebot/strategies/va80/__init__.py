"""VA NÁVRAT 1.0 — pravidlo 80 %: otvorenie mimo včerajšej value area a návrat do nej.

Prepis Rust stratégie (`rq_sdk`, roboquant.dev Templates), ktorú poslal používateľ 29. 10. 2026; zadanie týždňa 31. 10. 2026.
Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, Va80Config
from .engine import Va80Engine
from .hyperopt import Va80Hyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="va80",
    title="VA NÁVRAT 1.0",
    config_cls=Va80Config,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_1m",
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
    engine_factory=Va80Engine,
    freqtrade_class="Va80Strategy",
    multicharts_class="Va80Signal",
    multicharts_template="Va80_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=Va80Hyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "Va80Config", "Va80Engine", "CONFIG_DIR"]
