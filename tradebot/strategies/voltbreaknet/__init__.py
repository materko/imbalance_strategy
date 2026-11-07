"""Volt Break (C# jadro) — `voltbreak` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/voltbreak` do C# (`tradebot/strategies/voltbreak/ports/csharp`, kľúč `voltbreaknet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Profily `PRESIEL_SMERNICAMI_Volt_Break_*` prešli smernicou (trieda A auditu
7. 11. 2026, Sortino ≥ 2). Zhodu s Python predlohou `voltbreak` bar po bare stráži `tester/tests/test_csharp_parity_voltbreaknet.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..voltbreak import SPEC as BASE_SPEC
from .config import CONFIG_DIR, VoltBreakNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("voltbreaknet", ...)]`.
CSHARP_KEY = "voltbreaknet"

SPEC = replace(
    BASE_SPEC,
    key="voltbreaknet",
    title="Volt Break (C# jadro)",
    config_cls=VoltBreakNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="PRESIEL_SMERNICAMI_Volt_Break_1",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "voltbreak" / "ports" / "csharp",
    logic_of=None,
    freqtrade_class="VoltBreakNetStrategy",
    multicharts_class="VoltBreakNetSignal",
    multicharts_template="VoltBreakNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "VoltBreakNetConfig", "CONFIG_DIR"]
