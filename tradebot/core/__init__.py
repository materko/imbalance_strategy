"""Platformovo neutrálne jadro — nesmie importovať Freqtrade ani MultiCharts.

IBS názvy (`IBSConfig`, `IBSEngine`, `StateMachine`, `ZoneBook`…) žijú v
`tradebot.strategies.ibs`; tu sú dostupné lenivo cez `__getattr__`, aby staré importy
`from tradebot.core import IBSConfig` ďalej fungovali bez cyklu core ↔ strategies.
"""

from __future__ import annotations

from importlib import import_module

from .clock import ClockState, SessionClock, SessionSpec, SessionWindow
from .config import CONFIGS_ROOT, ConfigError, StrategyConfig, list_profiles, load_profile
from .drawing import (
    PAL,
    DrawBg,
    DrawBox,
    DrawCommand,
    DrawDelete,
    DrawKind,
    DrawLabel,
    DrawLine,
    DrawObject,
    DrawRegistry,
    DrawUpdate,
    LabelStyle,
    LineStyle,
    Palette,
)
from .engine import Engine, EngineOutput
from .history import BarHistory
from .orders import MarketContext, OrderAction, OrderIntent, StateEvent
from .risk import TradePlan, TrailingPlan, build_trade_plan, swing_stop_loss
from .types import (
    BTCUSD_COINBASE,
    BTCUSDT_BINANCE,
    BTCUSDT_BINANCE_SPOT,
    ETHUSDT_BINANCE,
    ETHUSDT_BINANCE_SPOT,
    INSTRUMENTS,
    MNQ,
    Bar,
    Direction,
    InstrumentSpec,
    OrderType,
    PanelPos,
    SizeSpec,
    SnapMode,
    TradeDirection,
)

#: Názvy, ktoré patria IBS stratégii — lenivo z `tradebot.strategies.ibs`.
_IBS_NAMES = frozenset({
    "IBSConfig", "CONFIG_DIR", "IBSEngine", "IBSEngineOutput", "StateMachine", "ZoneState",
    "Zone", "ZoneBook", "ZoneSource", "SdPattern", "detect_sd_pattern", "snap_time",
    "ImbalanceHit", "find_imbalance", "is_pin_bar", "is_engulfing",
    "HTFWindow", "htf_window_opens", "HTFFeeder",
})


def __getattr__(name: str):
    if name in _IBS_NAMES:
        return getattr(import_module("tradebot.strategies.ibs"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Bar",
    "Direction",
    "TradeDirection",
    "SnapMode",
    "OrderType",
    "PanelPos",
    "SizeSpec",
    "InstrumentSpec",
    "MNQ",
    "BTCUSD_COINBASE",
    "BTCUSDT_BINANCE",
    "BTCUSDT_BINANCE_SPOT",
    "ETHUSDT_BINANCE",
    "ETHUSDT_BINANCE_SPOT",
    "INSTRUMENTS",
    "StrategyConfig",
    "ConfigError",
    "CONFIGS_ROOT",
    "load_profile",
    "list_profiles",
    "SessionClock",
    "SessionSpec",
    "SessionWindow",
    "ClockState",
    "Palette",
    "PAL",
    "DrawKind",
    "DrawBox",
    "DrawLine",
    "DrawLabel",
    "DrawBg",
    "DrawCommand",
    "DrawDelete",
    "DrawObject",
    "DrawRegistry",
    "DrawUpdate",
    "LabelStyle",
    "LineStyle",
    "BarHistory",
    "Engine",
    "EngineOutput",
    "TradePlan",
    "TrailingPlan",
    "build_trade_plan",
    "swing_stop_loss",
    "OrderAction",
    "OrderIntent",
    "StateEvent",
    "MarketContext",
    *sorted(_IBS_NAMES),
]
