"""SD ZÓNY EURUSD (C# jadro) — SD ZÓNY EURUSD s jadrom v C#, aby bežala naživo v NinjaTraderi a MT5 na 6E / M6E.

Logika je prepis `tradebot/strategies/sdeur` do C# (`tradebot/csharp/TradeBot.Strategies/SdEurNet`, kľúč `sdeurnet`) s obalmi
vstupov z `EntryLayers`. Zhodu s Python predlohou `sdeur` bar po bare stráži `tester/tests/test_csharp_parity_6e.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import CSHARP_DIR

from ..sdeur import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SdEurNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("sdeurnet", ...)]` na triede `SdEurEngine`.
CSHARP_KEY = "sdeurnet"

SPEC = replace(
    BASE_SPEC,
    key="sdeurnet",
    title="SD ZÓNY EURUSD (C# jadro)",
    config_cls=SdEurNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="eurusd_6e_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=CSHARP_DIR / "TradeBot.Strategies" / "SdEurNet",
    freqtrade_class="SdEurNetStrategy",
    multicharts_class="SdEurNetSignal",
    multicharts_template="SdEurNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "SdEurNetConfig", "CONFIG_DIR"]
