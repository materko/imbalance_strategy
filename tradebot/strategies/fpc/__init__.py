"""FPC 1.0 — férová cena (Fair Pricing Theory podľa JJ Simona, Chart Fanatics).

Férová cena = open prvej sviečky obchodného okna (v deň správy o 8:30 cena pred správou). Prvý obchod okna
je pokračovanie v smere otváracej sviečky, ďalšie sú návraty k férovej cene na displacement alebo prieraz
štruktúry; tri straty po sebe ukončia okno. Pine verzia je mimo repozitára.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, FpcConfig, NewsMode, PmFair, TpMode, TradeDirection
from .engine import FpcEngine
from .hyperopt import FpcHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="fpc",
    title="FPC 1.0 — férová cena",
    config_cls=FpcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_1m",
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
    default_timeframe="1m",
    engine_factory=FpcEngine,
    freqtrade_class="FpcStrategy",
    multicharts_class="FpcSignal",
    multicharts_template="Fpc_Signal.py",
    fixed_size_field=None,
    risk_field="riskDollar",
    hyperopt_cls=FpcHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "FpcConfig", "FpcEngine", "NewsMode", "PmFair", "TpMode", "TradeDirection", "CONFIG_DIR"]
