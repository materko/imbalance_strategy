"""Trendlines — klasické trendovky cez pivoty a ich prerazenie.

Trendovky (klesajúci odpor, rastúca podpora) sa kreslia cez pivoty na vlastnom TF (5m až 4h),
ktorý si engine skladá z barov grafu; obchoduje sa prerazenie zatvorením, druhé zatvorenie
alebo retest. Stratégia nemá Pine predlohu — vznikla zo zápisu klasického postupu
„trendovka (3 dotyky) → prerazenie zatvorením → retest → pokračovanie".
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import (AnchorMode, CONFIG_DIR, EntryMode, LineSlope, SlMode, TradeDirection,
                     TrendlineConfig)
from .engine import TrendlineEngine
from .hyperopt import TrendlineHyperopt
from .meta import (FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES,
                   REMOVED_INPUTS)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="trendlines",
    title="Trendlines — prerazenie trendovky",
    config_cls=TrendlineConfig,
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
    engine_factory=TrendlineEngine,
    freqtrade_class="TrendlineStrategy",
    multicharts_class="TrendlineSignal",
    multicharts_template="Trendline_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=TrendlineHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "TrendlineConfig", "TrendlineEngine", "AnchorMode", "LineSlope", "EntryMode",
           "SlMode", "TradeDirection", "CONFIG_DIR"]
