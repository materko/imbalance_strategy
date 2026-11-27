"""TKS 1.0 MYM (C# jadro) — `tksmym` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/tks` do C# (`tradebot/strategies/tks/ports/csharp`, kľúč `tksmymnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `tksmym` bar po bare stráži
`tester/tests/test_csharp_parity_tks.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..tksnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, TksMymNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("tksmymnet", ...)]`.
CSHARP_KEY = "tksmymnet"

SPEC = replace(
    NET_SPEC,
    key="tksmymnet",
    base_key="tksmym",
    title="TKS 1.0 MYM (C# jadro)",
    config_cls=TksMymNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_MYM",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="TksMymNetStrategy",
    multicharts_class="TksMymNetSignal",
    multicharts_template="TksMymNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "TksMymNetConfig", "CONFIG_DIR"]
