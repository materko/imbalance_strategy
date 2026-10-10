"""SWEEP FVG 1.0 — výber likvidity → CHoCH / BOS → limitka na okraji najbližšieho FVG, SL za výber.

Zadanie používateľa 10. 10. 2026 (nákres v iCloude SWEEP-FVG). Pine predlohu stratégia nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import (CONFIG_DIR, BreakBy, BreakType, EntryModel, FvgPick, SweepFvgConfig, TpMode,
                     TradeDirection)
from .engine import SweepFvgEngine
from .hyperopt import SweepFvgHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="sweepfvg",
    title="SWEEP FVG 1.0 — výber LQ, CHoCH / BOS, FVG",
    config_cls=SweepFvgConfig,
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
    engine_factory=SweepFvgEngine,
    freqtrade_class="SweepFvgStrategy",
    multicharts_class="SweepFvgSignal",
    multicharts_template="SweepFvg_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=SweepFvgHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "SweepFvgConfig", "SweepFvgEngine", "BreakBy", "BreakType", "EntryModel", "FvgPick", "TpMode",
           "TradeDirection", "CONFIG_DIR"]
