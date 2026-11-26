"""MTK EMAS 1.0 — sledovanie trendu podľa kĺzavých priemerov (cena × priemer alebo kríženie), filter EMA 200, stop
a trailing v ATR; pravidlá zo štúdie Mac mini (iCloud KLZAKY-STUDIA, 25. 11. 2026). Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, MaType, MtkEmasConfig, SignalMode, TradeDirection
from .engine import MtkEmasEngine
from .hyperopt import MtkEmasHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="mtkemas",
    title="MTK EMAS 1.0",
    config_cls=MtkEmasConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_4h",
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
    default_timeframe="4h",
    engine_factory=MtkEmasEngine,
    freqtrade_class="MtkEmasStrategy",
    multicharts_class="MtkEmasSignal",
    multicharts_template="MtkEmas_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=MtkEmasHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "MtkEmasConfig", "MtkEmasEngine", "MaType", "SignalMode", "TradeDirection", "CONFIG_DIR"]
