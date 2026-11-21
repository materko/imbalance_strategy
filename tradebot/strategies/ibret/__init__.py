"""IB RETRACE 1.0 — prieraz Initial Balance (9:30–10:30 NY), vstup na návrate do IB, stop za úrovňou max retracementu.

Podľa videa IB Lab „Max Retracement Price“ (používateľ 20. 11. 2026). Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, EntryMode, IbRetConfig, TpMode, TradeDirection
from .engine import IbRetEngine
from .hyperopt import IbRetHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="ibret",
    title="IB RETRACE 1.0",
    config_cls=IbRetConfig,
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
    engine_factory=IbRetEngine,
    freqtrade_class="IbRetStrategy",
    multicharts_class="IbRetSignal",
    multicharts_template="IbRet_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=IbRetHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "IbRetConfig", "IbRetEngine", "EntryMode", "TpMode", "TradeDirection", "CONFIG_DIR"]
