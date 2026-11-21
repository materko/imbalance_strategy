"""IB RETRACE 1.0 MYM (C# jadro) — `ibretmym` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/ibret` do C# (`tradebot/strategies/ibret/ports/csharp`, kľúč `ibretmymnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `ibretmym` bar po bare stráži
`tester/tests/test_csharp_parity_ibret.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..ibretnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, IbRetMymNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("ibretmymnet", ...)]`.
CSHARP_KEY = "ibretmymnet"

SPEC = replace(
    NET_SPEC,
    key="ibretmymnet",
    base_key="ibretmym",
    title="IB RETRACE 1.0 MYM (C# jadro)",
    config_cls=IbRetMymNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="IbRetMymNetStrategy",
    multicharts_class="IbRetMymNetSignal",
    multicharts_template="IbRetMymNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "IbRetMymNetConfig", "CONFIG_DIR"]
