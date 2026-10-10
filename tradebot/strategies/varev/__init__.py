"""VALUE AREA REVERSION 1.0 — únik z value area so slabnúcim objemom, návrat dnu so silným objemom, cieľ opačná hrana.

Z videa LuxAlgo „I Turned A 4x World Cup Trader's Strategy Into An Indicator“ (youtube.com/watch?v=dUczefIYKIU),
stratégia Fabia Valentiniho. Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, ProfileSource, TpMode, TradeDirection, VaRevConfig
from .engine import VaRevEngine
from .hyperopt import VaRevHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="varev",
    title="VALUE AREA REVERSION 1.0 (Fabio Valentini)",
    config_cls=VaRevConfig,
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
    engine_factory=VaRevEngine,
    freqtrade_class="VaRevStrategy",
    multicharts_class="VaRevSignal",
    multicharts_template="VaRev_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=VaRevHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "VaRevConfig", "VaRevEngine", "ProfileSource", "TpMode", "TradeDirection", "CONFIG_DIR"]
