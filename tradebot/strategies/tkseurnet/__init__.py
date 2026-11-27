"""TKS 1.0 6E (C# jadro) — `tkseur` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/tks` do C# (`tradebot/strategies/tks/ports/csharp`, kľúč `tkseurnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `tkseur` bar po bare stráži
`tester/tests/test_csharp_parity_tks.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..tksnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, TksEurNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("tkseurnet", ...)]`.
CSHARP_KEY = "tkseurnet"

SPEC = replace(
    NET_SPEC,
    key="tkseurnet",
    base_key="tkseur",
    title="TKS 1.0 6E (C# jadro)",
    config_cls=TksEurNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_6E",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="TksEurNetStrategy",
    multicharts_class="TksEurNetSignal",
    multicharts_template="TksEurNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "TksEurNetConfig", "CONFIG_DIR"]
