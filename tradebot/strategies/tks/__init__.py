"""TKS 1.0 — obchod podľa NQ Kompasu (trend dňa na Nasdaqu): N sviečok za hranicou → vstup, SL na swing, TP v RR."""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, SlMode, TksConfig, TradeDirection
from .engine import Kompas, TksEngine
from .hyperopt import TksHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="tks",
    title="TKS 1.0 (NQ Kompas)",
    config_cls=TksConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_3m",
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
    default_timeframe="3m",
    engine_factory=TksEngine,
    freqtrade_class="TksStrategy",
    multicharts_class="TksSignal",
    multicharts_template="Tks_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=TksHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "TksConfig", "TksEngine", "Kompas", "TradeDirection", "SlMode", "CONFIG_DIR"]
