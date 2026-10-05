"""Fibo — návrat k Fibonacciho úrovniam po impulze a vstup na potvrdzovaciu sviečku.

Podľa videa Brada Goha (The Trading Geek): fibo cez impulz od swing dna po swing vrchol, čaká sa
na návrat k úrovniam 38,2 – 78,6 %, vstup až na znamenie otočky (tu IBS imbalance / pin bar), stop
za swing, cieľ na extenzii −27 %. Hrubý základ pre väčšiu stratégiu; nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, EntryModel, FiboConfig, LevelMode, SlMode, TpMode, TradeDirection
from .engine import FiboEngine
from .hyperopt import FiboHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="fibo",
    title="Fibo 1.0",
    config_cls=FiboConfig,
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
    engine_factory=FiboEngine,
    freqtrade_class="FiboStrategy",
    multicharts_class="FiboSignal",
    multicharts_template="Fibo_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=FiboHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "FiboConfig", "FiboEngine", "LevelMode", "EntryModel", "SlMode", "TpMode",
           "TradeDirection", "CONFIG_DIR"]
