"""WILLIAMS %R LONG 1.0 (C# jadro) — `wpr` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/wpr` do C# (`tradebot/strategies/wpr/ports/csharp`, kľúč `wprnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Profily `PRESIEL_SMERNICAMI_WILLIAMS_R_MNQ_*` prešli smernicou (trieda A auditu
7. 11. 2026, Sortino ≥ 2). Zhodu s Python predlohou `wpr` bar po bare stráži `tester/tests/test_csharp_parity_wprnet.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..wpr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, WprNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("wprnet", ...)]`.
CSHARP_KEY = "wprnet"

SPEC = replace(
    BASE_SPEC,
    key="wprnet",
    base_key="wpr",
    title="WILLIAMS %R LONG 1.0 (C# jadro)",
    config_cls=WprNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="PRESIEL_SMERNICAMI_WILLIAMS_R_MNQ_1",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "wpr" / "ports" / "csharp",
    logic_of=None,
    freqtrade_class="WprNetStrategy",
    multicharts_class="WprNetSignal",
    multicharts_template="WprNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "WprNetConfig", "CONFIG_DIR"]
