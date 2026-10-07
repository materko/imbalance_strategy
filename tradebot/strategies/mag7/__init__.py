"""SPX sila 1.0 (kľúč `mag7`, pôvodne „Mag7 + SPX sila") — sila pohybu S&P 500 od otvorenia NY, obchod na Nasdaqu.

Default (`spxOnly`) počíta ako Pine Mag7 1.0 v TradingView: silu len zo SPX — Pine 1.0 hľadá začiatok
seansy ako „sviečka mimo seansy → v seanse“ a akcie (sviečky len 9:30–15:59) nový deň nikdy nezachytia,
takže do sily nevstúpia (overené 7. 10. 2026). `spxOnly` vypnuté = SPX + akcie Mag7 s váhou `stockW` (Pine 1.1,
v TradingView aj tu PF ~1,0 od 12/2025 — používateľ ju odmietol). Pôvodný port je git tag `mag7-1.0`.

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
    title="SPX sila 1.0",
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
