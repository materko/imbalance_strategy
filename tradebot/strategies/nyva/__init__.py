"""NY VA BREAKOUT 1.0 — fixed range volume profile prvej hodiny NY (9:30–10:30) a prieraz nad VAH / pod VAL.

Zadanie používateľa 23. 10. 2026; najprv Pine skript na ručný test v TradingView (iCloud VOLUME-PROFILE),
táto verzia je na ručné testovanie vo webapp. Výsledky zatiaľ žiadne.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, NyVaConfig
from .engine import NyVaEngine
from .hyperopt import NyVaHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="nyva",
    title="NY VA BREAKOUT 1.0",
    config_cls=NyVaConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_3m",
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
    engine_factory=NyVaEngine,
    freqtrade_class="NyVaStrategy",
    multicharts_class="NyVaSignal",
    multicharts_template="NyVa_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=NyVaHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "NyVaConfig", "NyVaEngine", "CONFIG_DIR"]
