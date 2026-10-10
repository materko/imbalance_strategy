"""INTRADAY 1.0 — smernica obchodovania Martina: daily bias + likvidita PDH/PDL → SD zóna 1H → 15m → 5m → limitka.

Len NY seansa. Návrh a smernica: iCloud ZALOZNE-STRATEGIE/intraday/NAVRH.md, SMERNICA-OBCHODOVANIA.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, BiasMode, EntryModel, IntradayConfig, LiqMode, TpMode, TradeDirection
from .engine import IntradayEngine
from .hyperopt import IntradayHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="intraday",
    title="INTRADAY 1.0",
    config_cls=IntradayConfig,
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
    engine_factory=IntradayEngine,
    freqtrade_class="IntradayStrategy",
    multicharts_class="IntradaySignal",
    multicharts_template="Intraday_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=IntradayHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "IntradayConfig", "IntradayEngine", "BiasMode", "LiqMode", "EntryModel", "TpMode",
           "TradeDirection", "CONFIG_DIR"]
