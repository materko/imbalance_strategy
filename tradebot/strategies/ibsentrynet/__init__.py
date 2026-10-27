"""IBS Entry Zone (C# jadro) — IBS Entry Zone s jadrom v C#, aby bežala aj naživo v NinjaTraderi a MetaTraderi 5.

Logika je prepis `tradebot/strategies/ibsentry` do C# (`tradebot/strategies/ibsentry/csharp`) nad IBSNet
(`tradebot/strategies/ibs/csharp` — automat, zóny, entry modely) a generickým C# jadrom. Vlastné je len
to, čo pridáva predloha: zóny z veľkých imbalance (FVG, IFVG) z 5m/15m/30m/1h (`Fvg.cs`) a detekcia SD zón
synchronizovaná s dátami ako v `ibszones` (`HtfFeeder` so `ZoneSync`). To isté jadro spúšťajú:

* **NinjaTrader 8** — `tradebot/adapters/ninjatrader`, šablóna `deploy/ninjatrader/IBSEntryNet.cs`;
* **MetaTrader 5** — `tradebot/adapters/mt5`, šablóna `deploy/mt5/IBSEntryNet.mq5`;
* **Freqtrade** a emulátor MultiCharts cez most `tradebot/adapters/csharp` (webapp, história, analytika).

Parametre, profily a kresby sú zhodné s IBS Entry Zone; zhodu signálov bar po bare stráži
`tester/tests/test_csharp_parity_ibsentry.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..base import StrategySpec
from ..ibszones.htf import ZoneSyncHTFFeeder
from .config import CONFIG_DIR, IBSEntryNetConfig
from .hyperopt import IBSEntryNetHyperopt
from .meta import FEATURES, INERT_INPUTS, KIND_TITLES, LAYERS, PARAM_NOTES
from .params import GROUPS, PARAMS

#: Kľúč C# enginu — `[TradeBotEngine("ibsentrynet", ...)]` na triede `IbsEntryEngine`.
CSHARP_KEY = "ibsentrynet"

SPEC = StrategySpec(
    key="ibsentrynet",
    title="IBS Entry Zone (C# jadro)",
    config_cls=IBSEntryNetConfig,
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
    csharp_dir=STRATEGIES_DIR / "ibsentry" / "csharp",
    logic_of="ibsnet",  # C# engine dedí z ibsnet: polia predlohy číta jej C# kód
    freqtrade_class="IBSEntryNetStrategy",
    multicharts_class="IBSEntryNetSignal",
    multicharts_template="IBSEntryNet_Signal.py",
    informative_tfs=lambda cfg: ["1d" if str(cfg.zoneDetectionTF) == "D" else f"{int(cfg.zoneDetectionTF)}m"],
    htf_feeder=ZoneSyncHTFFeeder,
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="maxLossDollar",
    fixed_size_field="legacyPineSizing",
    hyperopt_cls=IBSEntryNetHyperopt,
)

__all__ = ["SPEC", "CSHARP_KEY", "IBSEntryNetConfig", "IBSEntryNetHyperopt", "CONFIG_DIR"]
