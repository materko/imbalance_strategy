"""Demo Donchian Breakout — ukážková druhá stratégia, ktorá overuje rámec pre viac stratégií.

Zdroj pravdy pre parametre: `pine/demo_breakout.pine`. Nie je to obchodné odporúčanie.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import REPO, StrategySpec
from .config import CONFIG_DIR, DemoBreakoutConfig, ExitMode
from .engine import DemoBreakoutEngine
from .meta import (
    FEATURES,
    INTENTIONAL_DEFAULT_DIFFS,
    KIND_TITLES,
    LAYERS,
    PARAM_NOTES,
    PORT_ONLY_META,
    REMOVED_INPUTS,
)

SPEC = StrategySpec(
    key="demo_breakout",
    title="Demo Donchian Breakout",
    config_cls=DemoBreakoutConfig,
    profile_dir=CONFIG_DIR,
    default_profile="binance_btcusdt_5m",
    pine_path=REPO / "pine" / "demo_breakout.pine",
    pine_input_count=8,
    removed_inputs=REMOVED_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    port_only_meta=PORT_ONLY_META,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="5m",
    engine_factory=DemoBreakoutEngine,
    freqtrade_class="DemoBreakoutStrategy",
    multicharts_class="DemoBreakoutSignal",
    multicharts_template="DemoBreakout_Signal.py",
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "DemoBreakoutConfig", "DemoBreakoutEngine", "ExitMode", "CONFIG_DIR"]
