"""SIGMA BREAKOUT 1.0 MYM (C# jadro) — `sigmamym` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/sigma` do C# (`tradebot/strategies/sigma/ports/csharp`, kľúč `sigmamymnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Ladenie a smernica na MYM bežia od 12. 11. 2026; prešlé profily pribudnú sem.
Zhodu s Python predlohou `sigmamym` bar po bare stráži `tester/tests/test_csharp_parity_mym.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..sigmamym import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SigmaMymNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("sigmamymnet", ...)]`.
CSHARP_KEY = "sigmamymnet"

SPEC = replace(
    BASE_SPEC,
    key="sigmamymnet",
    base_key="sigmamym",
    title="SIGMA BREAKOUT 1.0 MYM (C# jadro)",
    config_cls=SigmaMymNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "sigma" / "ports" / "csharp",
    logic_of=None,
    freqtrade_class="SigmaMymNetStrategy",
    multicharts_class="SigmaMymNetSignal",
    multicharts_template="SigmaMymNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "SigmaMymNetConfig", "CONFIG_DIR"]
