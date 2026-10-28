"""NB 1.0 — prieraz konsolidácie na grafe (M15) v smere trendu vyššieho TF (H4) so SMA 10 / 20.

Podľa videa TradeCZ s traderkou Nikolou (YouTube KBCvpjMWd5A), zadanie používateľa 28. 10. 2026. Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, NbConfig
from .engine import NbEngine
from .hyperopt import NbHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="nb",
    title="NB 1.0 — prieraz konsolidácie v smere H4 (SMA 10 / 20)",
    config_cls=NbConfig,
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
    engine_factory=NbEngine,
    freqtrade_class="NbStrategy",
    multicharts_class="NbSignal",
    multicharts_template="Nb_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=NbHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "NbConfig", "NbEngine", "CONFIG_DIR"]
