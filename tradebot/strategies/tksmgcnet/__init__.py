"""TKS 1.0 MGC (C# jadro) — `tksmgc` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/tks` do C# (`tradebot/strategies/tks/ports/csharp`, kľúč `tksmgcnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `tksmgc` bar po bare stráži
`tester/tests/test_csharp_parity_tks.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..tksnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, TksMgcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("tksmgcnet", ...)]`.
CSHARP_KEY = "tksmgcnet"

SPEC = replace(
    NET_SPEC,
    key="tksmgcnet",
    base_key="tksmgc",
    title="TKS 1.0 MGC (C# jadro)",
    config_cls=TksMgcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_3m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="TksMgcNetStrategy",
    multicharts_class="TksMgcNetSignal",
    multicharts_template="TksMgcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "TksMgcNetConfig", "CONFIG_DIR"]
