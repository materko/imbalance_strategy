"""Volt Break (kľúč `voltbreak`) — doslovný port Pine skriptu „Volt Break (NQ 30m)".

Long, keď 30m sviečka zavrie nad „noise" hranicou (open o polnoci CT + 30 % priemerného ATR) aj nad
VWAP od polnoci, medzi 10:00 a 14:30 CT; TP 800 $, SL 1 500 $ na kontrakt NQ, max 3 obchody denne.
Podľa videa „Hedge Fund Manager TOP 3 Strategies" (Matteo Conti / IQ Capital).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, AtrSource, VoltBreakConfig
from .engine import VoltBreakEngine
from .hyperopt import VoltBreakHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="voltbreak",
    title="Volt Break",
    config_cls=VoltBreakConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_30m",
    pine_path=CONFIG_DIR.parent / "docs" / "sources" / "volt_break.pine",
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
    default_timeframe="30m",
    engine_factory=VoltBreakEngine,
    freqtrade_class="VoltBreakStrategy",
    multicharts_class="VoltBreakSignal",
    multicharts_template="VoltBreak_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=VoltBreakHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "VoltBreakConfig", "VoltBreakEngine", "AtrSource", "CONFIG_DIR"]
