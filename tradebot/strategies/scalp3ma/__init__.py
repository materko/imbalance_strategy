"""Scalping 3MA + RSI + fraktál — obchod v smere trendu po potvrdení fraktálom.

Podľa videa „5 Minutová Scalping Stratégia" (Money Knowledge, Rene): tri vyhladené priemery 20 / 60 /
200 určia trend, RSI nad / pod 50 ho potvrdí, Williamsov fraktál je spúšťač; stop 5 pipov, cieľ 10 pipov,
posun stopu na vstup a výstup pri RSI cez 50. Stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, FractalSide, Scalp3MaConfig, SlMode, TradeDirection
from .engine import Scalp3MaEngine
from .hyperopt import Scalp3MaHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="scalp3ma",
    title="Scalping 3MA + RSI + fraktál 1.0",
    config_cls=Scalp3MaConfig,
    profile_dir=CONFIG_DIR,
    default_profile="eurusd_dukascopy_5m",
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
    engine_factory=Scalp3MaEngine,
    freqtrade_class="Scalp3MaStrategy",
    multicharts_class="Scalp3MaSignal",
    multicharts_template="Scalp3Ma_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=Scalp3MaHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "Scalp3MaConfig", "Scalp3MaEngine", "FractalSide", "SlMode", "TradeDirection", "CONFIG_DIR"]
