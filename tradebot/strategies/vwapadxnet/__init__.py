"""VWAP ADX Pullback (C# jadro) — VWAP ADX Pullback s jadrom v C#, aby bežala aj naživo v NinjaTraderi a MT5.

Logika je prepis `tradebot/strategies/vwapadx` do C# (`tradebot/strategies/vwapadx/csharp`) nad generickým
C# jadrom (seansový VWAP `SessionVwap.cs`, obaly vstupov `EntryLayers.cs`) a ADX z IBSNet (`Dmi`). To isté jadro
spúšťajú NinjaTrader 8 (`deploy/ninjatrader/VwapAdxNet.cs`), MetaTrader 5 (`deploy/mt5/VwapAdxNet.mq5`) aj
Freqtrade a emulátor MultiCharts cez most `tradebot/adapters/csharp`.

Parametre, profily a kresby sú zhodné s VWAP ADX Pullback; zhodu signálov bar po bare stráži
`tester/tests/test_csharp_parity_vwapadx.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..base import StrategySpec
from .config import CONFIG_DIR, VwapAdxNetConfig
from .hyperopt import VwapAdxNetHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("vwapadxnet", ...)]` na triede `VwapAdxEngine`.
CSHARP_KEY = "vwapadxnet"

SPEC = StrategySpec(
    key="vwapadxnet",
    title="VWAP ADX Pullback (C# jadro)",
    config_cls=VwapAdxNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_1m",
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
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "vwapadx" / "csharp",
    freqtrade_class="VwapAdxNetStrategy",
    multicharts_class="VwapAdxNetSignal",
    multicharts_template="VwapAdxNet_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=VwapAdxNetHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "CSHARP_KEY", "VwapAdxNetConfig", "CONFIG_DIR"]
