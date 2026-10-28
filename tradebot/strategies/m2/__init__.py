"""METODA 2 (M2) 1.0 — posledná opačná sviečka pred pohybom, potvrdenie celým telom, limitka na jej hrane, stop za ňou.

Podľa podkladov používateľa (`METODA_2.pdf`, `LTA - metoda2.pdf`, `m2 - advanced`), zadanie 28. 10. 2026. Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, M2Config
from .engine import M2Engine
from .hyperopt import M2Hyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="m2",
    title="M2",
    config_cls=M2Config,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_1m",
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
    engine_factory=M2Engine,
    freqtrade_class="M2Strategy",
    multicharts_class="M2Signal",
    multicharts_template="M2_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=M2Hyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "M2Config", "M2Engine", "CONFIG_DIR"]
