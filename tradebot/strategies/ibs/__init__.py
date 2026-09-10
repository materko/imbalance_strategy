"""IBS Imbalance Breakout Strategy — port Pine skriptu `docs/sources/imbalance_strategy_FULL.pine`."""

from __future__ import annotations

from pathlib import Path

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import REPO, StrategySpec
#: Zdrojové skripty stratégie (Pine) — pri nej, aby bol balík sebestačný.
SOURCES = Path(__file__).resolve().parent / "docs" / "sources"

from .config import CONFIG_DIR, CONSTRAINTS, DETECTION_TFS, PORT_ONLY_FIELDS, SIZE_FIELDS, IBSConfig
from .hyperopt import IBSHyperopt
from .engine import IBSEngine, IBSEngineOutput
from .htf import HTFFeeder, HTFWindow, htf_window_opens
from .params import GROUPS, PARAMS
from .meta import (
    FEATURES,
    INERT_INPUTS,
    INTENTIONAL_DEFAULT_DIFFS,
    KIND_TITLES,
    LAYERS,
    PARAM_NOTES,
    PARITY_FIELDS,
    REMOVED_INPUTS,
)
from .statemachine import StateMachine, ZoneState
from .ta import ImbalanceHit, find_imbalance, is_engulfing, is_pin_bar
from .zones import SdPattern, Zone, ZoneBook, ZoneSource, detect_sd_pattern, snap_time

SPEC = StrategySpec(
    key="ibs",
    title="IBS Imbalance Breakout",
    config_cls=IBSConfig,
    profile_dir=CONFIG_DIR,
    default_profile="golden_binance_btcusdt_3m",
    pine_path=SOURCES / "imbalance_strategy_FULL.pine",
    pine_input_count=115,
    removed_inputs=REMOVED_INPUTS,
    inert_inputs=INERT_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    parity_fields=PARITY_FIELDS,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="3m",
    engine_factory=IBSEngine,
    freqtrade_class="IBSImbalanceStrategy",
    multicharts_class="IBSSignal",
    multicharts_template="IBS_Signal.py",
    informative_tfs=lambda cfg: [f"{int(cfg.zoneDetectionTF)}m"],
    htf_feeder=HTFFeeder,
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="maxLossDollar",
    fixed_size_field="legacyPineSizing",
    hyperopt_cls=IBSHyperopt,
)

__all__ = [
    "SPEC", "IBSHyperopt",
    "IBSConfig", "CONFIG_DIR", "CONSTRAINTS", "DETECTION_TFS", "PORT_ONLY_FIELDS", "SIZE_FIELDS",
    "IBSEngine", "IBSEngineOutput", "StateMachine", "ZoneState",
    "HTFFeeder", "HTFWindow", "htf_window_opens",
    "ImbalanceHit", "find_imbalance", "is_engulfing", "is_pin_bar",
    "SdPattern", "Zone", "ZoneBook", "ZoneSource", "detect_sd_pattern", "snap_time",
    "REMOVED_INPUTS", "INERT_INPUTS", "INTENTIONAL_DEFAULT_DIFFS", "FEATURES", "PARAM_NOTES", "LAYERS", "KIND_TITLES",
]
