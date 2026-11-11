"""NOA 1.0 ES (C# jadro) — `noaes` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/noa` do C# (`tradebot/strategies/noa/ports/csharp`, kľúč `noaesnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `noaes` bar po bare stráži
`tester/tests/test_csharp_parity_noa.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..noanet import SPEC as NET_SPEC
from .config import CONFIG_DIR, NoaEsNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("noaesnet", ...)]`.
CSHARP_KEY = "noaesnet"

SPEC = replace(
    NET_SPEC,
    key="noaesnet",
    base_key="noaes",
    title="NOA 1.0 ES (C# jadro)",
    config_cls=NoaEsNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="NoaEsNetStrategy",
    multicharts_class="NoaEsNetSignal",
    multicharts_template="NoaEsNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "NoaEsNetConfig", "CONFIG_DIR"]
