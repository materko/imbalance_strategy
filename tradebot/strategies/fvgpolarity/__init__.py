"""FVG POLARITY — market obchod späť k práve vzniknutému FVG, cieľ je jeho dotyk.

Zadanie používateľa (1. 10. 2026, s nákresom): 15m graf; keď vznikne FVG, najbližšia sviečka
otvorí market obchod k medzere (po medvedom FVG long, po býčom short), drží sa až po dotyk
FVG — tam je TP — a stop je 20 bodov. Stop a veľkosť FVG sú nastaviteľné. Stratégia nemá Pine.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, FvgPolarityConfig, TpLevel, TradeDirection
from .engine import FvgPolarityEngine
from .hyperopt import FvgPolarityHyperopt
from .meta import (FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES,
                   REMOVED_INPUTS)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="fvgpolarity",
    title="FVG POLARITY",
    config_cls=FvgPolarityConfig,
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
    engine_factory=FvgPolarityEngine,
    freqtrade_class="FvgPolarityStrategy",
    multicharts_class="FvgPolaritySignal",
    multicharts_template="FvgPolarity_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=FvgPolarityHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "FvgPolarityConfig", "FvgPolarityEngine", "TpLevel", "TradeDirection", "CONFIG_DIR"]
