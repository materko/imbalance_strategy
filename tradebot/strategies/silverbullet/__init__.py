"""Silver Bullet 1.0 (ICT) — okno 10:00–11:00 NY, výber likvidity, FVG v protismere, limitka na FVG.

Zadanie používateľa 17. 10. 2026 (obrázok „ICT SILVER BULLET — 1 10–11 AM · 2 SWEEP · 3 FVG“). Pine predlohu nemá.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, EntryLevel, EntryType, SilverBulletConfig, TpMode, TradeDirection
from .engine import SilverBulletEngine
from .hyperopt import SilverBulletHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="silverbullet",
    title="Silver Bullet 1.0 (ICT) — 10–11 NY, sweep, FVG",
    config_cls=SilverBulletConfig,
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
    engine_factory=SilverBulletEngine,
    freqtrade_class="SilverBulletStrategy",
    multicharts_class="SilverBulletSignal",
    multicharts_template="SilverBullet_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=SilverBulletHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "SilverBulletConfig", "SilverBulletEngine", "EntryLevel", "EntryType", "TpMode", "TradeDirection",
           "CONFIG_DIR"]
