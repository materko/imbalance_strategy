"""IBS FVG + IFVG — IBS entry model len nad zónami z imbalance.

Zdroj zón sú výhradne fair value gapy z 5m, 15m, 30m a 1h (`ibsentry/fvg.py`) a ich
inverzie (IFVG). S/R úrovne, likvidita a Elliott sú natvrdo vypnuté a vo formulári nie sú; SD pattern je
vypnutý defaultom, takže
stratégia je čistý test otázky „drží IBS entry model na imbalance zónach?". Engine,
parametre aj kreslenie sú z IBS Entry Zone — líšia sa len defaulty configu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá

from ..base import StrategySpec
from ..ibsentry.engine import IBSEntryZoneEngine
from ..ibszones.htf import ZoneSyncHTFFeeder
from .config import CONFIG_DIR, IBSFvgConfig
from .hyperopt import IBSFvgHyperopt
from .meta import FEATURES, INERT_INPUTS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="ibsfvg",
    title="IBS FVG + IFVG",
    config_cls=IBSFvgConfig,
    profile_dir=CONFIG_DIR,
    default_profile="golden_binance_btcusdt_3m",
    inert_inputs=INERT_INPUTS,
    removed_inputs=REMOVED_INPUTS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="3m",
    engine_factory=IBSEntryZoneEngine,
    logic_of="ibsentry",  # celá logika vrátane FVG/IFVG je z IBS Entry Zone; tu sú len defaulty
    freqtrade_class="IBSFvgStrategy",
    multicharts_class="IBSFvgSignal",
    multicharts_template="IBSFvg_Signal.py",
    informative_tfs=lambda cfg: ["1d" if str(cfg.zoneDetectionTF) == "D" else f"{int(cfg.zoneDetectionTF)}m"],
    htf_feeder=ZoneSyncHTFFeeder,
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="maxLossDollar",
    fixed_size_field="legacyPineSizing",
    hyperopt_cls=IBSFvgHyperopt,
)

__all__ = ["SPEC", "IBSFvgConfig", "IBSFvgHyperopt", "CONFIG_DIR"]
