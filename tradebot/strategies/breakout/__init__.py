"""Breakout — prerazenie prvej sviečky otvorenia newyorskej seansy.

Prvá 5-minútová sviečka po 9:30 New York dá high a low. Obchoduje sa **zavretie**
sviečky za tou hranicou (nie prepichnutie knôtom), stop ide pod/nad tú istú sviečku
a cieľ je nastaviteľný násobok rizika (1:1, 1:1,5, 1:2 …). Vstupuje sa na 1m, 2m alebo
3m grafe; otváracia sviečka preto prichádza z informatívneho TF, aby bola na všetkých
troch tá istá. Stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import BreakoutConfig, CONFIG_DIR, OpeningLength, OrderKind, TradeDirection
from .engine import BreakoutEngine
from .htf import ClosedHtfBar, OpeningFeeder
from .hyperopt import BreakoutHyperopt
from .meta import (FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES,
                   REMOVED_INPUTS)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="breakout",
    title="Breakout — prerazenie prvej sviečky NY openu",
    config_cls=BreakoutConfig,
    profile_dir=CONFIG_DIR,
    default_profile="nas100_dukascopy_3m",
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
    engine_factory=BreakoutEngine,
    freqtrade_class="BreakoutStrategy",
    multicharts_class="BreakoutSignal",
    multicharts_template="Breakout_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    #: Otváracia sviečka je 5-minútová, ale graf beží na 1m/2m/3m — z barov grafu sa
    #: poskladať nedá (5 sa dvomi ani tromi nedelí), preto informatívny TF.
    informative_tfs=lambda cfg: [cfg.openingMinutes.timeframe],
    htf_feeder=lambda cfg, chart_tf: OpeningFeeder(cfg, chart_tf),
    hyperopt_cls=BreakoutHyperopt,
)

__all__ = ["SPEC", "BreakoutConfig", "BreakoutEngine", "OpeningFeeder", "ClosedHtfBar",
           "OpeningLength", "OrderKind", "TradeDirection", "CONFIG_DIR"]
