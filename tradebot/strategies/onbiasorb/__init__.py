"""Overnight Bias ORB (kľúč `onbiasorb`) — doslovný port Pine skriptu „Overnight Bias ORB (NQ 15m)".

Smer dňa podľa toho, v ktorej tretine overnight rangu (polnoc – 8:30 CT) je open 8:30; prerazenie prvej
15m sviečky v tom smere s ADX > 20; SL 30 % priemerného ATR, TP 3 × SL, exit 14:30 CT, jeden obchod denne.
Podľa videa „Hedge Fund Manager TOP 3 Strategies" (Matteo Conti / IQ Capital).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, AtrSource, OnBiasOrbConfig
from .engine import OnBiasOrbEngine
from .hyperopt import OnBiasOrbHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="onbiasorb",
    title="Overnight Bias ORB",
    config_cls=OnBiasOrbConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_15m",
    pine_path=CONFIG_DIR.parent / "docs" / "sources" / "overnight_bias_orb.pine",
    pine_input_count=11,
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
    engine_factory=OnBiasOrbEngine,
    freqtrade_class="OnBiasOrbStrategy",
    multicharts_class="OnBiasOrbSignal",
    multicharts_template="OnBiasOrb_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=OnBiasOrbHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "OnBiasOrbConfig", "OnBiasOrbEngine", "AtrSource", "CONFIG_DIR"]
