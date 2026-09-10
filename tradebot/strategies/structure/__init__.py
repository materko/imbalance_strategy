"""Market Structure (BOS / CHoCH) — druhá ostrá stratégia registry.

Iný archetyp než IBS: tá je prerazenie v NY seanse, táto stojí na tržnej štruktúre
a vo variante `sweep` je priamo protitrendová. Zdroj pravdy pre parametre:
`docs/sources/structure.pine`.
"""

from __future__ import annotations

from pathlib import Path

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec

#: Zdrojové skripty stratégie (Pine) — pri nej, aby bol balík sebestačný.
SOURCES = Path(__file__).resolve().parent / "docs" / "sources"

from .config import CONFIG_DIR, EntryMode, ExitMode, SessionTZ, SlMode, StructureConfig
from .engine import StructureEngine
from .hyperopt import StructureHyperopt
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
    key="structure",
    title="Market Structure BOS / CHoCH",
    config_cls=StructureConfig,
    profile_dir=CONFIG_DIR,
    default_profile="binance_btcusdt_5m",
    pine_path=SOURCES / "structure.pine",
    pine_input_count=18,
    removed_inputs=REMOVED_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="5m",
    engine_factory=StructureEngine,
    freqtrade_class="StructureStrategy",
    multicharts_class="StructureSignal",
    multicharts_template="Structure_Signal.py",
    informative_tfs=None,
    htf_feeder=None,
    # Čo z balíka potrebuje analytika: kresby s plánom obchodu, pole s rizikom
    # a vedomosti o ladení. `tp_box` sa v režime `exitMode = structure` nekreslí —
    # obchod tam pevný cieľ nemá, takže plánovaný RR tých obchodov naozaj neexistuje.
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="riskDollar",
    hyperopt_cls=StructureHyperopt,
)

__all__ = ["SPEC", "StructureConfig", "StructureEngine", "StructureHyperopt",
           "EntryMode", "ExitMode", "SlMode", "SessionTZ", "CONFIG_DIR"]
