"""IBS Imbalance Breakout Strategy — port Pine skriptu `pine/imbalance_strategy_FULL.pine`."""

from __future__ import annotations

from ..base import StrategySpec
from .config import CONFIG_DIR, CONSTRAINTS, DETECTION_TFS, PORT_ONLY_FIELDS, SIZE_FIELDS, IBSConfig
from .engine import IBSEngine, IBSEngineOutput
from .htf import HTFFeeder, HTFWindow, htf_window_opens
from .statemachine import StateMachine, ZoneState
from .ta import ImbalanceHit, find_imbalance, is_engulfing, is_pin_bar
from .zones import SdPattern, Zone, ZoneBook, ZoneSource, detect_sd_pattern, snap_time

SPEC = StrategySpec(
    key="ibs",
    title="IBS Imbalance Breakout",
    config_cls=IBSConfig,
    profile_dir=CONFIG_DIR,
    default_profile="golden_binance_btcusdt_3m",
)

__all__ = [
    "SPEC",
    "IBSConfig", "CONFIG_DIR", "CONSTRAINTS", "DETECTION_TFS", "PORT_ONLY_FIELDS", "SIZE_FIELDS",
    "IBSEngine", "IBSEngineOutput", "StateMachine", "ZoneState",
    "HTFFeeder", "HTFWindow", "htf_window_opens",
    "ImbalanceHit", "find_imbalance", "is_engulfing", "is_pin_bar",
    "SdPattern", "Zone", "ZoneBook", "ZoneSource", "detect_sd_pattern", "snap_time",
]
