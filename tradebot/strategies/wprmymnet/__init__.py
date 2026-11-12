"""WILLIAMS %R LONG 1.0 MYM (C# jadro) — `wprmym` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/wpr` do C# (`tradebot/strategies/wpr/ports/csharp`, kľúč `wprmymnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Ladenie a smernica na MYM bežia od 12. 11. 2026; prešlé profily pribudnú sem.
Zhodu s Python predlohou `wprmym` bar po bare stráži `tester/tests/test_csharp_parity_mym.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..wprmym import SPEC as BASE_SPEC
from .config import CONFIG_DIR, WprMymNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("wprmymnet", ...)]`.
CSHARP_KEY = "wprmymnet"

SPEC = replace(
    BASE_SPEC,
    key="wprmymnet",
    base_key="wprmym",
    title="WILLIAMS %R LONG 1.0 MYM (C# jadro)",
    config_cls=WprMymNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_15m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "wpr" / "ports" / "csharp",
    logic_of=None,
    freqtrade_class="WprMymNetStrategy",
    multicharts_class="WprMymNetSignal",
    multicharts_template="WprMymNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "WprMymNetConfig", "CONFIG_DIR"]
