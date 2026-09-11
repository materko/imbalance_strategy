"""Divergence — divergencie indikátorov v smere supertrendu vyšších TF.

Port `DivergenceStrategy` (Freqtrade, 2022, `divergence_strategy.py`): na Heikin Ashi
sviečkach grafu sa hľadajú divergencie (RSI, MACD, stochastik, OBV, …) algoritmom
„Divergence for Many Indicators v4", obchoduje sa len v smere supertrendu na 1h aj 4h,
pri pullbacku na grafe a mimo období, keď vyššie TF ukazujú divergenciu proti obchodu.
Výstup: stop z ATR, dvojstupňový trailing, prerazenie supertrendu 4h pre stratový obchod.
Čo sa portom zmenilo: `docs/PORT.md`. Stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, DivergenceConfig, DivSource, EntryMode, SearchDiv
from .engine import DivergenceEngine
from .hyperopt import DivergenceHyperopt
from .meta import (
    FEATURES,
    INTENTIONAL_DEFAULT_DIFFS,
    KIND_TITLES,
    LAYERS,
    PARAM_NOTES,
    REMOVED_INPUTS,
)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="divergence",
    title="Divergence — divergencie indikátorov v smere supertrendu",
    config_cls=DivergenceConfig,
    profile_dir=CONFIG_DIR,
    default_profile="binance_btcusdt_15m",
    pine_path=None,
    pine_input_count=0,
    removed_inputs=REMOVED_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="15m",
    engine_factory=DivergenceEngine,
    freqtrade_class="DivergenceStrategy",
    multicharts_class="DivergenceSignal",
    multicharts_template="Divergence_Signal.py",
    informative_tfs=None,
    htf_feeder=None,
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="riskDollar",
    hyperopt_cls=DivergenceHyperopt,
)

__all__ = ["SPEC", "DivergenceConfig", "DivergenceEngine", "DivergenceHyperopt",
           "DivSource", "SearchDiv", "EntryMode", "CONFIG_DIR"]
