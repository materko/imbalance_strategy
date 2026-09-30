"""VWAP OP (kľúč `vwapop`) — doslovný port Pine skriptu "Drift VWAP Pullback Strategy".

Prvý pullback k VWAP v smere jeho driftu na vyššom TF (predvolene 15m, zobrazený na 5m
grafe). Na rozdiel od `vwapdrift` (voľná rekonštrukcia rovnakej myšlienky) je toto presný
port konkrétneho Pine v6 skriptu, ktorý autor prilepil: `docs/sources/vwap_op.pine`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, VwapOpConfig
from .engine import VwapOpEngine
from .hyperopt import VwapOpHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="vwapop",
    title="VWAP OP",
    config_cls=VwapOpConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_5m",
    pine_path=(CONFIG_DIR.parent / "docs" / "sources" / "vwap_op.pine"),
    pine_input_count=21,
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
    engine_factory=VwapOpEngine,
    freqtrade_class="VwapOpStrategy",
    multicharts_class="VwapOpSignal",
    multicharts_template="VwapOp_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=VwapOpHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "VwapOpConfig", "VwapOpEngine", "CONFIG_DIR"]
