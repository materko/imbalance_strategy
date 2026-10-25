"""VWAP ORB (C# jadro) — VWAP ORB 1.5 s jadrom v C#, aby bežala aj naživo v NinjaTraderi a MetaTraderi 5.

Logika je prepis `tradebot/strategies/vwaporb` do C# (`csharp/TradeBot.Strategies/VwapOrbNet`) nad ORBNet
(`csharp/TradeBot.Strategies/OrbNet`) a generickým C# jadrom (`csharp/TradeBot.Core`, seansový VWAP
`SessionVwap.cs`, obaly vstupov `EntryLayers.cs`). To isté jadro spúšťajú:

* **NinjaTrader 8** — `tradebot/adapters/ninjatrader`, šablóna `deploy/ninjatrader/VwapOrbNet.cs`;
* **MetaTrader 5** — `tradebot/adapters/mt5`, šablóna `deploy/mt5/VwapOrbNet.mq5`;
* **Freqtrade** a emulátor MultiCharts cez most `tradebot/adapters/csharp` (webapp, história, analytika).

Parametre, profily a kresby sú zhodné s VWAP ORB; zhodu signálov bar po bare stráži
`tester/tests/test_csharp_parity_vwaporb.py`. Jediné, čo C# port nemá, je stop posúvaný s VWAP
(`vwapStop`, `vwapTp`) — config ho odmietne (`config.py`).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import CSHARP_DIR

from ..base import StrategySpec
from ..vwaporb.hyperopt import VwapOrbHyperopt
from .config import CONFIG_DIR, VwapOrbNetConfig
from .meta import FEATURES, INERT_INPUTS, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("vwaporbnet", ...)]` na triede `VwapOrbEngine`.
CSHARP_KEY = "vwaporbnet"

SPEC = StrategySpec(
    key="vwaporbnet",
    title="VWAP ORB 1.5 (C# jadro)",
    config_cls=VwapOrbNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_5m",
    pine_path=None,
    pine_input_count=0,
    removed_inputs=REMOVED_INPUTS,
    inert_inputs=INERT_INPUTS,
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
    csharp_dir=CSHARP_DIR / "TradeBot.Strategies" / "VwapOrbNet",
    logic_of="orbnet",  # C# engine dedí z orbnet: polia predlohy číta jej C# kód
    freqtrade_class="VwapOrbNetStrategy",
    multicharts_class="VwapOrbNetSignal",
    multicharts_template="VwapOrbNet_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=VwapOrbHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "CSHARP_KEY", "VwapOrbNetConfig", "CONFIG_DIR"]
