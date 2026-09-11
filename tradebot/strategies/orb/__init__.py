"""ORB — Opening Range Breakout.

Prvých N minút seansy tvorí opening range; obchoduje sa prerazenie jeho hranice.
Zdroj pravdy pre parametre: `docs/sources/orb.pine`.
"""

from __future__ import annotations

from pathlib import Path

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec

#: Zdrojové skripty stratégie (Pine) — pri nej, aby bol balík sebestačný.
SOURCES = Path(__file__).resolve().parent / "docs" / "sources"

from .config import (CONFIG_DIR, EntryMode, ORBConfig, SessionMode, SessionWindow,
                     SlMode, TpMode, TradeDirection)
from .engine import ORBEngine
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
    key="orb",
    title="ORB — Opening Range Breakout",
    config_cls=ORBConfig,
    profile_dir=CONFIG_DIR,
    default_profile="nas100_dukascopy_3m",
    pine_path=SOURCES / "orb.pine",
    pine_input_count=40,
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
    default_timeframe="3m",
    engine_factory=ORBEngine,
    freqtrade_class="ORBStrategy",
    multicharts_class="ORBSignal",
    multicharts_template="ORB_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "ORBConfig", "ORBEngine", "EntryMode", "SessionMode", "SessionWindow",
           "SlMode", "TpMode", "TradeDirection", "CONFIG_DIR"]
