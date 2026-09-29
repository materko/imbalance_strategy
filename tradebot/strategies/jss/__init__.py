"""JSS 1.0 — BOS / CHoCH, SD zóna, ktorá ho spôsobila, a vstup pri návrate do nej.

Na TF štruktúry (skladá sa z barov grafu) príde BOS alebo CHoCH; nájde sa SD zóna na začiatku
nohy, ktorá swing prerazila; pri prvom návrate do zóny limitka na jej hranu alebo IBS imbalance /
pin bar na grafe (nižší TF). Stop za protiľahlou hranou zóny, cieľ RR alebo extrém nohy BOS.
Pravidlá zadal používateľ 29. 9. 2026; stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import (CONFIG_DIR, EntryModel, JssConfig, TpMode, TradeDirection, TriggerMode, ZoneEdge,
                     ZoneType)
from .engine import JssEngine
from .hyperopt import JssHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="jss",
    title="JSS 1.0 — BOS a SD zóna",
    config_cls=JssConfig,
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
    engine_factory=JssEngine,
    freqtrade_class="JssStrategy",
    multicharts_class="JssSignal",
    multicharts_template="Jss_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=JssHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "JssConfig", "JssEngine", "TriggerMode", "ZoneType", "ZoneEdge", "EntryModel", "TpMode",
           "TradeDirection", "CONFIG_DIR"]
