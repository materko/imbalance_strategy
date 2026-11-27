"""TKS 1.0 ES (C# jadro) — `tkses` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/tks` do C# (`tradebot/strategies/tks/ports/csharp`, kľúč `tksesnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `tkses` bar po bare stráži
`tester/tests/test_csharp_parity_tks.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..tksnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, TksEsNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("tksesnet", ...)]`.
CSHARP_KEY = "tksesnet"

SPEC = replace(
    NET_SPEC,
    key="tksesnet",
    base_key="tkses",
    title="TKS 1.0 ES (C# jadro)",
    config_cls=TksEsNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_ES",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="TksEsNetStrategy",
    multicharts_class="TksEsNetSignal",
    multicharts_template="TksEsNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "TksEsNetConfig", "CONFIG_DIR"]
