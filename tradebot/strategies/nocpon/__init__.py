"""NOC + PONDELOK 1.0 — nočný drift Nasdaqu (15:55 → 3:00 NY) a pondelok (9:30 → 15:55), len nad SMA 100 dní.

Z prieskumu Nasdaqu 18. 10. 2026 (MNQ 5/2019 – 9/2026, 1 kontrakt, poplatok 1 bod): 209 obch/rok, WR 57 %,
PF 1,47, DD 3 455 $; okná 21/22 1,19 | 22/23 1,27 | 23/24 1,52 | 24/25 1,45 | 25/26 1,38.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, NocPonConfig
from .engine import NocPonEngine
from .hyperopt import NocPonHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="nocpon",
    title="NOC + PONDELOK 1.0",
    config_cls=NocPonConfig,
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
    engine_factory=NocPonEngine,
    freqtrade_class="NocPonStrategy",
    multicharts_class="NocPonSignal",
    multicharts_template="NocPon_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=NocPonHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "NocPonConfig", "NocPonEngine", "CONFIG_DIR"]
