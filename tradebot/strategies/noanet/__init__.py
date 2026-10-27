"""NOA 1.0 (C# jadro) — NOA 1.0 (Noise Area, Concretum) s jadrom v C#, aby bežala aj naživo v NinjaTraderi a MT5.

Logika je prepis `tradebot/strategies/noa` do C# (`tradebot/strategies/noa/ports/csharp`) nad generickým C# jadrom
(obaly vstupov `EntryLayers.cs`). To isté jadro spúšťajú NinjaTrader 8 (`deploy/ninjatrader/NoaNet.cs`), MetaTrader 5
(`deploy/mt5/NoaNet.mq5`) aj Freqtrade a emulátor MultiCharts cez most `tradebot/adapters/csharp`.

Parametre, profily a kresby sú zhodné s NOA 1.0; zhodu signálov bar po bare stráži
`tester/tests/test_csharp_parity_noa.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..base import StrategySpec
from .config import CONFIG_DIR, NoaNetConfig
from .hyperopt import NoaNetHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("noanet", ...)]` na triede `NoaEngine`.
CSHARP_KEY = "noanet"

SPEC = StrategySpec(
    key="noanet",
    title="NOA 1.0 (C# jadro)",
    config_cls=NoaNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_5m",
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
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "noa" / "ports" / "csharp",
    freqtrade_class="NoaNetStrategy",
    multicharts_class="NoaNetSignal",
    multicharts_template="NoaNet_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=NoaNetHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "CSHARP_KEY", "NoaNetConfig", "CONFIG_DIR"]
