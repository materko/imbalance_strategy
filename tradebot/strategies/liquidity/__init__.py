"""Liquidity — likvidita na swing vrcholoch a dnách, jej vybratie a cesta k ďalšej likvidite.

Likvidita sa značí klasicky, ako ju značí trader: z výrazného swing vrcholu (buy-side) a dna
(sell-side) na viacerých TF (5m až 4h) sa ťahá úroveň, kým ju cena nezoberie; rovnaké
vrcholy/dná sa zlúčia. Obchoduje sa sweep (otočka), prerazenie (pokračovanie k ďalšej
likvidite) alebo cesta k najbližšej nevybratej likvidite, so vstupom cez IBS imbalance alebo
pin bar. Stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import (CONFIG_DIR, EntryModel, EntryOrder, LiquidityConfig, SlMode, TpMode,
                     TradeDirection, TradeMode)
from .engine import LiquidityEngine
from .hyperopt import LiquidityHyperopt
from .meta import (FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES,
                   REMOVED_INPUTS)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="liquidity",
    title="Liquidity — likvidita, sweep a cesta k nej",
    config_cls=LiquidityConfig,
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
    engine_factory=LiquidityEngine,
    freqtrade_class="LiquidityStrategy",
    multicharts_class="LiquiditySignal",
    multicharts_template="Liquidity_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=LiquidityHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "LiquidityConfig", "LiquidityEngine", "TradeMode", "EntryModel", "EntryOrder",
           "SlMode", "TpMode", "TradeDirection", "CONFIG_DIR"]
