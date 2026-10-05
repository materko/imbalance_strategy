"""VWAP Session 1.0 (kľúč `vwapdrift`) — Drift VWAP Pullback: návrat ceny k VWAP v smere jeho sklonu.

Do 2026-09-28 sa volala „Drift VWAP Pullback"; kľúč ostal, aby história behov patrila k nej.

VWAP ukotvený na otvorení 9:30 New York (alebo klasický seansový VWAP), počítaný z 15m
sviečok a zobrazený na 5m grafe; sklon VWAP („drift") určí smer dňa a obchoduje sa prvý
pullback k nemu. Stratégia nemá Pine predlohu — vznikla z rozhovoru s Matteom na kanáli
IQCapital (2026), ktorý ju predstavil ako „drift VWAP pullback" pre NQ futures.
Samotný VWAP je v jadre (`tradebot.core.vwap`).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import (CONFIG_DIR, EntryMode, RuleSet, SlMode, TradeDirection, VwapAnchor, VwapDriftConfig,
                     VwapPeriod)
from .engine import VwapDriftEngine
from .hyperopt import VwapDriftHyperopt
from .meta import (FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES,
                   REMOVED_INPUTS)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="vwapdrift",
    title="VWAP Session 1.0",
    config_cls=VwapDriftConfig,
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
    engine_factory=VwapDriftEngine,
    freqtrade_class="VwapDriftStrategy",
    multicharts_class="VwapDriftSignal",
    multicharts_template="VwapDrift_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=VwapDriftHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "RuleSet", "VwapDriftConfig", "VwapDriftEngine", "VwapAnchor", "VwapPeriod", "EntryMode",
           "SlMode", "TradeDirection", "CONFIG_DIR"]
