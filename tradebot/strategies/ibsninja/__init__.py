"""IBSNinja — IBS Imbalance Breakout s jadrom v C#.

Logika je prepis `tradebot/strategies/ibs` do C# (`csharp/TradeBot.Strategies/IbsNinja`) nad
generickým C# jadrom (`csharp/TradeBot.Core`). To isté jadro spúšťajú dva adaptéry:

* **NinjaTrader 8** natívne — `tradebot/adapters/ninjatrader` (NinjaScript), šablóna
  `deploy/ninjatrader/IBSNinja.cs`;
* **Freqtrade** cez most `tradebot/adapters/csharp` — preto sa tu zvyšku TradeBota javí
  ako každá iná stratégia (webapp, história, analytika, hyperopt).

Parametre, profily a kresby sú zhodné s IBS; zhodu signálov stráži
`tradebot/tests/test_ibsninja_parity.py` (bar po bare proti Python enginu).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import CSHARP_DIR

from ..base import StrategySpec
from ..ibs.htf import HTFFeeder
from .config import CONFIG_DIR, IBSNinjaConfig
from .hyperopt import IBSNinjaHyperopt
from .meta import FEATURES, INERT_INPUTS, KIND_TITLES, LAYERS, PARAM_NOTES
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("ibsninja", ...)]` na triede `IbsEngine`.
CSHARP_KEY = "ibsninja"

SPEC = StrategySpec(
    key="ibsninja",
    title="IBSNinja Imbalance Breakout (C# jadro)",
    config_cls=IBSNinjaConfig,
    profile_dir=CONFIG_DIR,
    default_profile="golden_binance_btcusdt_3m",
    inert_inputs=INERT_INPUTS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="3m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=CSHARP_DIR / "TradeBot.Strategies" / "IbsNinja",
    freqtrade_class="IBSNinjaStrategy",
    multicharts_class="IBSNinjaSignal",
    multicharts_template="IBSNinja_Signal.py",
    informative_tfs=lambda cfg: ["1d" if str(cfg.zoneDetectionTF) == "D" else f"{int(cfg.zoneDetectionTF)}m"],
    htf_feeder=HTFFeeder,
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="maxLossDollar",
    fixed_size_field="legacyPineSizing",
    hyperopt_cls=IBSNinjaHyperopt,
)

__all__ = ["SPEC", "CSHARP_KEY", "IBSNinjaConfig", "IBSNinjaHyperopt", "CONFIG_DIR"]
