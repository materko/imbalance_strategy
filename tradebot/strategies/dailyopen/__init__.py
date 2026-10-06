"""DAILY OPEN 1.0 — long prieraz nad zavretím polnoci NY (podľa videa Ali Caseyho, StatOasis).

Úroveň = zavretie sviečky, ktorá končí o polnoci NY; od 8:00 long, keď cena prerazí úroveň + 30 bodov,
stop 50 bodov (1 000 $ na NQ), výstup o 16:00 NY, jeden obchod za deň.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, BreakMode, DailyOpenConfig, EntryMode, TradeDirection
from .engine import DailyOpenEngine
from .hyperopt import DailyOpenHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="dailyopen",
    title="DAILY OPEN 1.0",
    config_cls=DailyOpenConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_60m",
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
    default_timeframe="1h",
    engine_factory=DailyOpenEngine,
    freqtrade_class="DailyOpenStrategy",
    multicharts_class="DailyOpenSignal",
    multicharts_template="DailyOpen_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=DailyOpenHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "DailyOpenConfig", "DailyOpenEngine", "BreakMode", "EntryMode", "TradeDirection", "CONFIG_DIR"]
