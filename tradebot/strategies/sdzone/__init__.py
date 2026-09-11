"""SD Zones — supply/demand zóny zo vzoru „báza + impulz".

Zóna vzniká tam, odkiaľ cena impulzívne odišla z krátkej konsolidácie; obchoduje sa
**prvý návrat** do nej. Štyri formácie: Rally-Base-Rally a Drop-Base-Drop (pokračovacie),
Drop-Base-Rally a Rally-Base-Drop (obratové).

Rozdiel oproti stratégii `ibs`: tá v zóne hľadá imbalance cez päťstavový automat, tu sa
obchoduje samotný návrat do čerstvej zóny. Metodika nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import (CONFIG_DIR, EntryMode, PatternSet, SDZoneConfig, SlMode, TpMode,
                     TradeDirection, ZoneMode)
from .engine import SDZoneEngine
from .meta import (FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES,
                   REMOVED_INPUTS)
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="sdzone",
    title="SD Zones — supply/demand z bázy a impulzu",
    config_cls=SDZoneConfig,
    profile_dir=CONFIG_DIR,
    default_profile="xau_dukascopy_15m",
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
    default_timeframe="15m",
    engine_factory=SDZoneEngine,
    freqtrade_class="SDZoneStrategy",
    multicharts_class="SDZoneSignal",
    multicharts_template="SDZone_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "SDZoneConfig", "SDZoneEngine", "EntryMode", "PatternSet", "SlMode",
           "TpMode", "TradeDirection", "ZoneMode", "CONFIG_DIR"]
