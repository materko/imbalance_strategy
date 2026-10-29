"""IVB 1.0 — Initial Volatility Breakout: prieraz IB 9:30–10:00 NY pri stlačenom IB a náraste objemu.

Prepis Rust stratégie `IvbStrategy` (`rq_sdk`), ktorú poslal používateľ 29. 10. 2026 „len pre porovnanie“. Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, IvbConfig
from .engine import IvbEngine
from .hyperopt import IvbHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="ivb",
    title="IVB 1.0 — Initial Volatility Breakout",
    config_cls=IvbConfig,
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
    engine_factory=IvbEngine,
    freqtrade_class="IvbStrategy",
    multicharts_class="IvbSignal",
    multicharts_template="Ivb_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=IvbHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "IvbConfig", "IvbEngine", "CONFIG_DIR"]
