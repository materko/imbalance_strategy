"""Gap Fill — obchodovanie výplne otváracej medzery.

Medzera medzi včerajším close a dnešným open sa vypĺňa častejšie, než nie — a čím je
menšia, tým skôr. Stratégia ju fáduje: gap up predáva, gap down kupuje, cieľom je
včerajší close.

Defaulty vychádzajú z merania na 2 791 dňoch NQ (2015–2025), viď `docs/ANALYTIKA.md`.
Pine zdroj balík nemá — popisy parametrov sú v `params.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec

from .config import CONFIG_DIR, EntryMode, GapConfig, GapDirection, SlMode, TpMode
from .engine import GapEngine
from .meta import (
    FEATURES,
    INTENTIONAL_DEFAULT_DIFFS,
    KIND_TITLES,
    LAYERS,
    PARAM_NOTES,
    REMOVED_INPUTS,
)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="gap",
    title="Gap Fill — výplň otváracej medzery",
    config_cls=GapConfig,
    profile_dir=CONFIG_DIR,
    default_profile="nas100_dukascopy_5m",
    removed_inputs=REMOVED_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="5m",
    engine_factory=GapEngine,
    freqtrade_class="GapStrategy",
    multicharts_class="GapSignal",
    multicharts_template="Gap_Signal.py",
    informative_tfs=None,
    htf_feeder=None,
    sl_kind="sl_box",
    tp_kind="tp_box",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
)

__all__ = ["SPEC", "GapConfig", "GapEngine", "EntryMode", "GapDirection", "SlMode", "TpMode",
           "CONFIG_DIR"]
