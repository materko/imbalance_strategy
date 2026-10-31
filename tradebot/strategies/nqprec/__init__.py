"""NQ PRECISION 1.0 — OR 9:30–9:45, snímka 9:59:55, filtre RVOL a režim ATR, výstup po 8 min.

Prepis Rust stratégie (`rq_sdk`, roboquant.dev Templates), ktorú poslal používateľ 29. 10. 2026; zadanie týždňa 31. 10. 2026.
Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, NqprecConfig
from .engine import NqprecEngine
from .hyperopt import NqprecHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="nqprec",
    title="NQ PRECISION 1.0",
    config_cls=NqprecConfig,
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
    engine_factory=NqprecEngine,
    freqtrade_class="NqprecStrategy",
    multicharts_class="NqprecSignal",
    multicharts_template="Nqprec_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=NqprecHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "NqprecConfig", "NqprecEngine", "CONFIG_DIR"]
