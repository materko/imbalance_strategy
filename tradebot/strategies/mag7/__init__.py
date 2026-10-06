"""Mag7 + SPX sila 1.1 — sila pohybu Mag7 a S&P 500 od otvorenia NY, obchod na Nasdaqu.

Verzie: 1.0 = sila zo všetkých 8 symbolov (git tag `mag7-1.0`); 1.1 = váha akcií `stockW`
(default 1 = správanie 1.0, 0 = sila len zo SPX ako v TradingView).

Port Pine stratégie „Mag7 + SPX sila od NY open" (Pine mimo repozitára). Symboly sily číta feeder
`data.py` z 1m skladu sviečok (akcie Mag7 z IBKR, S&P 500 = Dukascopy US500).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, Mag7Config, SlMode
from .data import Mag7Feeder
from .engine import Mag7Engine
from .hyperopt import Mag7Hyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="mag7",
    title="Mag7 + SPX sila 1.1",
    config_cls=Mag7Config,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_15m",
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
    engine_factory=Mag7Engine,
    freqtrade_class="Mag7Strategy",
    multicharts_class="Mag7Signal",
    multicharts_template="Mag7_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=Mag7Hyperopt,
    informative_tfs=None,
    htf_feeder=Mag7Feeder,
)

__all__ = ["SPEC", "Mag7Config", "Mag7Engine", "Mag7Feeder", "SlMode", "CONFIG_DIR"]
