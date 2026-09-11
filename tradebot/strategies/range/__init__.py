"""Range Breakout — konsolidácia kdekoľvek na grafe, jej prerazenie a pokračovanie.

Na rozdiel od ORB nie je range viazaný na otvorenie seansy: hľadá sa priebežne v posuvnom
okne. Stratégia nemá Pine predlohu — vznikla zo zápisu klasického postupu
„konsolidácia → prerazenie → (retest) → pokračovanie".
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import (BoundaryMode, CONFIG_DIR, EntryMode, RangeConfig, SlMode, TpMode,
                     TradeDirection)
from .engine import RangeEngine
from .meta import (FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES,
                   REMOVED_INPUTS)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="range",
    title="Range Breakout — konsolidácia a jej prerazenie",
    config_cls=RangeConfig,
    profile_dir=CONFIG_DIR,
    default_profile="nas100_dukascopy_3m",
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
    default_timeframe="3m",
    engine_factory=RangeEngine,
    freqtrade_class="RangeStrategy",
    multicharts_class="RangeSignal",
    multicharts_template="Range_Signal.py",
    risk_field="riskDollar",
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "RangeConfig", "RangeEngine", "BoundaryMode", "EntryMode", "SlMode",
           "TpMode", "TradeDirection", "CONFIG_DIR"]
