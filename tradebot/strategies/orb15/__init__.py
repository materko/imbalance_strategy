"""ORB 15/5 1.0 — OR 9:30–9:45, prieraz zavretím 5m, stop druhá strana OR, RR 2.

Prepis Rust stratégie (`rq_sdk`, roboquant.dev Templates), ktorú poslal používateľ 29. 10. 2026; zadanie týždňa 31. 10. 2026.
Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, Orb15Config
from .engine import Orb15Engine
from .hyperopt import Orb15Hyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="orb15",
    title="ORB 15/5 1.0",
    config_cls=Orb15Config,
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
    engine_factory=Orb15Engine,
    freqtrade_class="Orb15Strategy",
    multicharts_class="Orb15Signal",
    multicharts_template="Orb15_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=Orb15Hyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "Orb15Config", "Orb15Engine", "CONFIG_DIR"]
