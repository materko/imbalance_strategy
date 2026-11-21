"""IB RETRACE 1.0 MGC (C# jadro) — `ibretmgc` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/ibret` do C# (`tradebot/strategies/ibret/ports/csharp`, kľúč `ibretmgcnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `ibretmgc` bar po bare stráži
`tester/tests/test_csharp_parity_ibret.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..ibretnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, IbRetMgcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("ibretmgcnet", ...)]`.
CSHARP_KEY = "ibretmgcnet"

SPEC = replace(
    NET_SPEC,
    key="ibretmgcnet",
    base_key="ibretmgc",
    title="IB RETRACE 1.0 MGC (C# jadro)",
    config_cls=IbRetMgcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="IbRetMgcNetStrategy",
    multicharts_class="IbRetMgcNetSignal",
    multicharts_template="IbRetMgcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "IbRetMgcNetConfig", "CONFIG_DIR"]
