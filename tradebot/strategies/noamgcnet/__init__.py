"""NOA 1.0 MGC (C# jadro) — `noamgc` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/noa` do C# (`tradebot/strategies/noa/ports/csharp`, kľúč `noamgcnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `noamgc` bar po bare stráži
`tester/tests/test_csharp_parity_noa.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..noanet import SPEC as NET_SPEC
from .config import CONFIG_DIR, NoaMgcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("noamgcnet", ...)]`.
CSHARP_KEY = "noamgcnet"

SPEC = replace(
    NET_SPEC,
    key="noamgcnet",
    base_key="noamgc",
    title="NOA 1.0 MGC (C# jadro)",
    config_cls=NoaMgcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="NoaMgcNetStrategy",
    multicharts_class="NoaMgcNetSignal",
    multicharts_template="NoaMgcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "NoaMgcNetConfig", "CONFIG_DIR"]
