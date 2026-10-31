"""SPRÁVY 3.0 — zlato (MGC) po červených správach USA: pre každú správu vlastné pravidlo (FOMC pred správou, CPI, PPI, PCE, JOLTS).

Výskum a zadanie používateľa 29. 10. 2026 (iCloud SPRAVY). Kalendár správ je v balíku (`calendar.json`).
Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, SpravyConfig
from .engine import SpravyEngine
from .hyperopt import SpravyHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="spravy",
    title="SPRÁVY 3.0",
    config_cls=SpravyConfig,
    profile_dir=CONFIG_DIR,
    default_profile="profil_1",
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
    engine_factory=SpravyEngine,
    freqtrade_class="SpravyStrategy",
    multicharts_class="SpravySignal",
    multicharts_template="Spravy_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=SpravyHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "SpravyConfig", "SpravyEngine", "CONFIG_DIR"]
