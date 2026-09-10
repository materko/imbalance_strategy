"""Demo Donchian Breakout — ukážková druhá stratégia, ktorá overuje rámec pre viac stratégií.

Zdroj pravdy pre parametre: `docs/sources/demo_breakout.pine`. Nie je to obchodné odporúčanie.
"""

from __future__ import annotations

from pathlib import Path

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import REPO, StrategySpec
#: Zdrojové skripty stratégie (Pine) — pri nej, aby bol balík sebestačný.
SOURCES = Path(__file__).resolve().parent / "docs" / "sources"

from .config import CONFIG_DIR, DemoBreakoutConfig, ExitMode
from .engine import DemoBreakoutEngine
from .hyperopt import DemoBreakoutHyperopt
from .params import GROUPS, PARAMS
from .meta import (
    FEATURES,
    INTENTIONAL_DEFAULT_DIFFS,
    KIND_TITLES,
    LAYERS,
    PARAM_NOTES,
    REMOVED_INPUTS,
)

SPEC = StrategySpec(
    key="demo_breakout",
    title="Demo Donchian Breakout",
    config_cls=DemoBreakoutConfig,
    profile_dir=CONFIG_DIR,
    default_profile="binance_btcusdt_5m",
    pine_path=SOURCES / "demo_breakout.pine",
    pine_input_count=8,
    removed_inputs=REMOVED_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    param_meta=PARAMS,
    param_groups=GROUPS,
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
    # Čo z balíka potrebuje analytika: kresby s plánom obchodu, pole s rizikom
    # a vedomosti o ladení. Bez nich beží tiež, len bez vzdialenosti stopu,
    # plánovaného RR, prepočtu na iný účet a odkazov „preladiť tento parameter".
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="riskDollar",
    hyperopt_cls=DemoBreakoutHyperopt,
)

__all__ = ["SPEC", "DemoBreakoutConfig", "DemoBreakoutEngine", "DemoBreakoutHyperopt",
           "ExitMode", "CONFIG_DIR"]
