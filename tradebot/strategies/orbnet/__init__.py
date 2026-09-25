"""ORBNet — ORB (Opening Range Breakout) s jadrom v C#.

Logika je prepis `tradebot/strategies/orb` do C# (`csharp/TradeBot.Strategies/OrbNet`) nad
generickým C# jadrom (`csharp/TradeBot.Core`). To isté jadro spúšťajú dva adaptéry:

* **NinjaTrader 8** natívne — `tradebot/adapters/ninjatrader` (NinjaScript), šablóna
  `deploy/ninjatrader/ORBNet.cs`;
* **Freqtrade** cez most `tradebot/adapters/csharp` — preto sa tu zvyšku TradeBota javí
  ako každá iná stratégia (webapp, história, analytika).

Parametre, profily a kresby sú zhodné s ORB; zhodu signálov stráži
`tester/tests/test_csharp_parity_orb.py` (bar po bare proti Python enginu).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import CSHARP_DIR

from ..base import StrategySpec
from .config import CONFIG_DIR, ORBNetConfig
from .meta import FEATURES, KIND_TITLES, LAYERS, PARAM_NOTES
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("orbnet", ...)]` na triede `OrbEngine`.
CSHARP_KEY = "orbnet"

SPEC = StrategySpec(
    key="orbnet",
    title="ORBNet Opening Range Breakout (C# jadro)",
    config_cls=ORBNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="nas100_dukascopy_3m",
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
    csharp_dir=CSHARP_DIR / "TradeBot.Strategies" / "OrbNet",
    freqtrade_class="ORBNetStrategy",
    multicharts_class="ORBNetSignal",
    multicharts_template="ORBNet_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "CSHARP_KEY", "ORBNetConfig", "CONFIG_DIR"]
