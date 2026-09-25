"""IBS Entry Zone — IBS so vstupmi filtrovanými veľkými imbalance zónami.

Nad IBS pribúda jedna vrstva (`fvg.py`): fair value gapy z 5m, 15m, 30m a 1h, ktoré sa
držia v čase a rozhodujú, či sa vstup pustí. Entry modely IBS (imbalance, pin bar,
engulfing) sa **nemenia** — vrstva ich len zapína a vypína podľa toho, kde je cena.

Vyššie TF si vrstva skladá z barov grafu rovnakým pravidlom ako `tradebot/core/candles.py`,
takže nepotrebuje informatívne páry navyše a Freqtrade aj MultiCharts vidia to isté.
Detekcia SD zón je synchronizovaná ako v `ibszones`, nie ako v `ibs`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá

from ..base import StrategySpec
from ..ibszones.htf import ZoneSyncHTFFeeder
from .config import CONFIG_DIR, IBSEntryZoneConfig
from .engine import IBSEntryZoneEngine
from .fvg import FVG_TIMEFRAMES, FvgDetector, FvgHit, TimeframeAggregator
from .hyperopt import IBSEntryZoneHyperopt
from .meta import FEATURES, INERT_INPUTS, KIND_TITLES, LAYERS, PARAM_NOTES
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="ibsentry",
    title="IBS Entry Zone",
    config_cls=IBSEntryZoneConfig,
    profile_dir=CONFIG_DIR,
    default_profile="golden_binance_btcusdt_3m",
    inert_inputs=INERT_INPUTS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="3m",
    engine_factory=IBSEntryZoneEngine,
    logic_of="ibs",  # entry modely, state machine a zóny sú z IBS; vlastná je vrstva FVG
    freqtrade_class="IBSEntryZoneStrategy",
    multicharts_class="IBSEntryZoneSignal",
    multicharts_template="IBSEntryZone_Signal.py",
    informative_tfs=lambda cfg: ["1d" if str(cfg.zoneDetectionTF) == "D" else f"{int(cfg.zoneDetectionTF)}m"],
    htf_feeder=ZoneSyncHTFFeeder,
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="maxLossDollar",
    fixed_size_field="legacyPineSizing",
    hyperopt_cls=IBSEntryZoneHyperopt,
)

__all__ = [
    "SPEC", "IBSEntryZoneConfig", "IBSEntryZoneEngine", "IBSEntryZoneHyperopt",
    "FVG_TIMEFRAMES", "FvgDetector", "FvgHit", "TimeframeAggregator", "CONFIG_DIR",
]
