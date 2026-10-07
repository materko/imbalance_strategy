"""ASIA SWEEP 1.0 — londýnska seansa vyberie likviditu Ázie, vstup do protismeru (IBS imbalance / pin bar).

Range Ázie (20:00–00:00 NY), jeho prieraz v Londýne (2:00–5:00 NY) a návrat do rangu, vstup do protismeru
vstupným modelom, stop za sweep, cieľ RR / opačná strana rangu / stred / naked POC; voliteľný filter naked POC
z volume profilu predošlého dňa. Pine predlohu stratégia nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, AsiaSweepConfig, EntryModel, SlMode, TpMode, TradeDirection
from .engine import AsiaSweepEngine
from .hyperopt import AsiaSweepHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="asiasweep",
    title="ASIA SWEEP 1.0",
    config_cls=AsiaSweepConfig,
    profile_dir=CONFIG_DIR,
    default_profile="eurusd_dukascopy_5m",
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
    engine_factory=AsiaSweepEngine,
    freqtrade_class="AsiaSweepStrategy",
    multicharts_class="AsiaSweepSignal",
    multicharts_template="AsiaSweep_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=AsiaSweepHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "AsiaSweepConfig", "AsiaSweepEngine", "EntryModel", "SlMode", "TpMode", "TradeDirection",
           "CONFIG_DIR"]
