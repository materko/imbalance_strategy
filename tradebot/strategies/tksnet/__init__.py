"""TKS 1.0 (C# jadro) — TKS 1.0 (NQ Kompas) s jadrom v C#, aby bežala aj naživo v NinjaTraderi a MT5.

Logika je prepis `tradebot/strategies/tks` do C# (`tradebot/csharp/TradeBot.Strategies/TksNet`: NQ Kompas aj pravidlá vstupu)
nad generickým C# jadrom (obaly vstupov `EntryLayers.cs`). To isté jadro spúšťajú NinjaTrader 8
(`deploy/ninjatrader/TksNet.cs`), MetaTrader 5 (`deploy/mt5/TksNet.mq5`) aj Freqtrade a emulátor MultiCharts cez most
`tradebot/adapters/csharp`.

Parametre, profily a kresby sú zhodné s TKS 1.0; zhodu signálov bar po bare stráži
`tester/tests/test_csharp_parity_tks.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import CSHARP_DIR

from ..base import StrategySpec
from .config import CONFIG_DIR, TksNetConfig
from .hyperopt import TksNetHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("tksnet", ...)]` na triede `TksEngine`.
CSHARP_KEY = "tksnet"

SPEC = StrategySpec(
    key="tksnet",
    title="TKS 1.0 (C# jadro)",
    config_cls=TksNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_3m",
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
    default_timeframe="3m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=CSHARP_DIR / "TradeBot.Strategies" / "TksNet",
    freqtrade_class="TksNetStrategy",
    multicharts_class="TksNetSignal",
    multicharts_template="TksNet_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=TksNetHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "CSHARP_KEY", "TksNetConfig", "CONFIG_DIR"]
