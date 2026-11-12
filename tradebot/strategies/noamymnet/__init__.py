"""NOA 1.0 MYM (C# jadro) — `noamym` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/noa` do C# (`tradebot/strategies/noa/ports/csharp`, kľúč `noamymnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `noamym` bar po bare stráži
`tester/tests/test_csharp_parity_mym.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..noanet import SPEC as NET_SPEC
from .config import CONFIG_DIR, NoaMymNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("noamymnet", ...)]`.
CSHARP_KEY = "noamymnet"

SPEC = replace(
    NET_SPEC,
    key="noamymnet",
    base_key="noamym",
    title="NOA 1.0 MYM (C# jadro)",
    config_cls=NoaMymNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="NoaMymNetStrategy",
    multicharts_class="NoaMymNetSignal",
    multicharts_template="NoaMymNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "NoaMymNetConfig", "CONFIG_DIR"]
