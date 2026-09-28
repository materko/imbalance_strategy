"""VWAP ORB 1.0 — New York opening range, vstup keď VWAP prerazí za range a cena je tam tiež.

Zadanie testera (2026-09-28): klasický ORB z New York rangu (od 9:30 NY = 15:30 SEČ) a VWAP
od toho istého času; long, keď VWAP prerazí nad high rangu a zároveň je tam aj cena (short
zrkadlovo), vstup market, stop na opačnej strane rangu, RR nastaviteľné. Logika je ORB
(`tradebot/strategies/orb`), vlastná je len podmienka VWAP (`engine.py`).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, VwapOrbConfig
from .engine import VwapOrbEngine
from .meta import (FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES,
                   REMOVED_INPUTS)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="vwaporb",
    title="VWAP ORB 1.0",
    config_cls=VwapOrbConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_5m",
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
    default_timeframe="5m",
    engine_factory=VwapOrbEngine,
    freqtrade_class="VwapOrbStrategy",
    multicharts_class="VwapOrbSignal",
    multicharts_template="VwapOrb_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    informative_tfs=None,
    htf_feeder=None,
    logic_of="orb",  # range, stop, cieľ aj koniec seansy sú z ORB; vlastná je podmienka VWAP
)

__all__ = ["SPEC", "VwapOrbConfig", "VwapOrbEngine", "CONFIG_DIR"]
