"""IBS Imbalance Breakout Strategy — port Pine skriptu `pine/imbalance_strategy_FULL.pine`."""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import REPO, StrategySpec
from .config import CONFIG_DIR, CONSTRAINTS, DETECTION_TFS, PORT_ONLY_FIELDS, SIZE_FIELDS, IBSConfig
from .engine import IBSEngine, IBSEngineOutput
from .htf import HTFFeeder, HTFWindow, htf_window_opens
from .meta import (
    FEATURES,
    INTENTIONAL_DEFAULT_DIFFS,
    KIND_TITLES,
    LAYERS,
    PARAM_NOTES,
    PORT_ONLY_META,
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
    pine_path=REPO / "pine" / "imbalance_strategy_FULL.pine",
    pine_input_count=115,
    removed_inputs=REMOVED_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    port_only_meta=PORT_ONLY_META,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="3m",
    engine_factory=IBSEngine,
    freqtrade_class="IBSImbalanceStrategy",
    multicharts_class="IBSSignal",
    informative_tfs=lambda cfg: [f"{int(cfg.zoneDetectionTF)}m"],
    htf_feeder=HTFFeeder,
)

__all__ = [
    "SPEC",
    "IBSConfig", "CONFIG_DIR", "CONSTRAINTS", "DETECTION_TFS", "PORT_ONLY_FIELDS", "SIZE_FIELDS",
    "IBSEngine", "IBSEngineOutput", "StateMachine", "ZoneState",
    "HTFFeeder", "HTFWindow", "htf_window_opens",
    "ImbalanceHit", "find_imbalance", "is_engulfing", "is_pin_bar",
    "SdPattern", "Zone", "ZoneBook", "ZoneSource", "detect_sd_pattern", "snap_time",
    "REMOVED_INPUTS", "INTENTIONAL_DEFAULT_DIFFS", "PORT_ONLY_META", "FEATURES", "PARAM_NOTES", "LAYERS", "KIND_TITLES",
]
