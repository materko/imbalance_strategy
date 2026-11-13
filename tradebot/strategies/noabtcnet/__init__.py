"""NOA 1.0 BTC (C# jadro) — `noabtc` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/noa` do C# (`tradebot/strategies/noa/ports/csharp`, kľúč `noabtcnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `noabtc` bar po bare stráži
`tester/tests/test_csharp_parity_btc.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..noanet import SPEC as NET_SPEC
from .config import CONFIG_DIR, NoaBtcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("noabtcnet", ...)]`.
CSHARP_KEY = "noabtcnet"

SPEC = replace(
    NET_SPEC,
    key="noabtcnet",
    base_key="noabtc",
    title="NOA 1.0 BTC (C# jadro)",
    config_cls=NoaBtcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="NoaBtcNetStrategy",
    multicharts_class="NoaBtcNetSignal",
    multicharts_template="NoaBtcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "NoaBtcNetConfig", "CONFIG_DIR"]
