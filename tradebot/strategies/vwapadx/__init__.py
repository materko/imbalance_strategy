"""VWAP ADX (kľúč `vwapadx`) — doslovný port Pine skriptu „VWAP ADX Pullback (NQ 1m)".

Po prerazení opening rangu 8:30–9:00 CT nahor sa čaká na pullback k VWAP a zavretie nad ním;
vstupuje sa, keď je ADX nad prahom a prestal rásť. TP/SL z extrémov posledných barov, časový exit
15:55 CT, len long. Podľa videa „Hedge Fund Manager TOP 3 Strategies" (Matteo Conti / IQ Capital).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, VwapAdxConfig, VwapAnchor
from .engine import VwapAdxEngine
from .hyperopt import VwapAdxHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="vwapadx",
    title="VWAP ADX Pullback",
    config_cls=VwapAdxConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_1m",
    pine_path=CONFIG_DIR.parent / "docs" / "sources" / "vwap_adx.pine",
    pine_input_count=9,
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
    default_timeframe="1m",
    engine_factory=VwapAdxEngine,
    freqtrade_class="VwapAdxStrategy",
    multicharts_class="VwapAdxSignal",
    multicharts_template="VwapAdx_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=VwapAdxHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "VwapAdxConfig", "VwapAdxEngine", "VwapAnchor", "CONFIG_DIR"]
