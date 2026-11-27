"""MTK EMAS 1.0 (C# jadro) — MTK EMAS 1.0 s jadrom v C#, aby bežala aj naživo v NinjaTraderi a MT5.

Logika je prepis `tradebot/strategies/mtkemas` do C# (`tradebot/strategies/mtkemas/ports/csharp`) nad generickým C# jadrom
(obaly vstupov `EntryLayers.cs`). To isté jadro spúšťajú NinjaTrader 8 (`deploy/ninjatrader/MtkEmasNet.cs`),
MetaTrader 5 (`deploy/mt5/MtkEmasNet.mq5`) aj Freqtrade a emulátor MultiCharts cez most `tradebot/adapters/csharp`.

Parametre, profily a kresby sú zhodné s MTK EMAS 1.0; zhodu signálov bar po bare stráži
`tester/tests/test_csharp_parity_mtkemas.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..base import StrategySpec
from .config import CONFIG_DIR, MtkEmasNetConfig
from .hyperopt import MtkEmasNetHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("mtkemasnet", ...)]` na triede `MtkEmasEngine`.
CSHARP_KEY = "mtkemasnet"

SPEC = StrategySpec(
    key="mtkemasnet",
    base_key="mtkemas",
    title="MTK EMAS 1.0 (C# jadro)",
    config_cls=MtkEmasNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_MNQ",
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
    default_timeframe="4h",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "mtkemas" / "ports" / "csharp",
    freqtrade_class="MtkEmasNetStrategy",
    multicharts_class="MtkEmasNetSignal",
    multicharts_template="MtkEmasNet_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=MtkEmasNetHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "CSHARP_KEY", "MtkEmasNetConfig", "CONFIG_DIR"]
