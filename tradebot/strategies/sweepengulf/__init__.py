"""SWEEPING ENGULF 1.0 — sviečka vyberie extrém predošlej a pohltí ju; market, stop za manipuláciu, cieľ RR.

Z videa LuxAlgo „I Backtested This Viral Trading Strategy“ (youtube.com/watch?v=oxZj1kSye-g). Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, EngulfMode, PrevCandle, SlMethod, SweepEngulfConfig, TradeDirection
from .engine import SweepEngulfEngine
from .hyperopt import SweepEngulfHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="sweepengulf",
    title="SWEEPING ENGULF 1.0 (LuxAlgo video)",
    config_cls=SweepEngulfConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_4h",
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
    default_timeframe="4h",
    engine_factory=SweepEngulfEngine,
    freqtrade_class="SweepEngulfStrategy",
    multicharts_class="SweepEngulfSignal",
    multicharts_template="SweepEngulf_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=SweepEngulfHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "SweepEngulfConfig", "SweepEngulfEngine", "EngulfMode", "PrevCandle", "SlMethod",
           "TradeDirection", "CONFIG_DIR"]
