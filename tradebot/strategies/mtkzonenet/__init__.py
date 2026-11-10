"""MTK ZONE (C# jadro) — MTK ZONE s jadrom v C#, aby bežala aj naživo v NinjaTraderi a MT5.

Logika je prepis `tradebot/strategies/mtkzone` do C# (`tradebot/strategies/mtkzone/ports/csharp`) nad generickým
C# jadrom (obaly vstupov `EntryLayers.cs`) a skladaním vyšších TF z IBS Entry Zone (`TimeframeAggregator`).
To isté jadro spúšťajú NinjaTrader 8 (`deploy/ninjatrader/MtkZoneNet.cs`), MetaTrader 5 (`deploy/mt5/MtkZoneNet.mq5`)
aj Freqtrade a emulátor MultiCharts cez most `tradebot/adapters/csharp`.

Zhodu signálov aj kresieb bar po bare stráži `tester/tests/test_csharp_parity_mtkzone.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..base import StrategySpec
from .config import CONFIG_DIR, MtkZoneNetConfig
from .hyperopt import MtkZoneNetHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("mtkzonenet", ...)]` na triede `MtkZoneEngine`.
CSHARP_KEY = "mtkzonenet"

SPEC = StrategySpec(
    key="mtkzonenet",
    base_key="mtkzone",
    title="MTK ZONE (C# jadro)",
    config_cls=MtkZoneNetConfig,
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
    csharp_dir=STRATEGIES_DIR / "mtkzone" / "ports" / "csharp",
    freqtrade_class="MtkZoneNetStrategy",
    multicharts_class="MtkZoneNetSignal",
    multicharts_template="MtkZoneNet_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=MtkZoneNetHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "CSHARP_KEY", "MtkZoneNetConfig", "CONFIG_DIR"]
