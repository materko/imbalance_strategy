"""SIGMA BREAKOUT 1.0 (C# jadro) — `sigma` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/sigma` do C# (`tradebot/strategies/sigma/ports/csharp`, kľúč `sigmanet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Profily `PRESIEL_SMERNICAMI_SIGMA_MNQ_*` prešli smernicou (trieda A auditu
7. 11. 2026, Sortino ≥ 2). Zhodu s Python predlohou `sigma` bar po bare stráži `tester/tests/test_csharp_parity_sigmanet.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..sigma import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SigmaNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("sigmanet", ...)]`.
CSHARP_KEY = "sigmanet"

SPEC = replace(
    BASE_SPEC,
    key="sigmanet",
    title="SIGMA BREAKOUT 1.0 (C# jadro)",
    config_cls=SigmaNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="PRESIEL_SMERNICAMI_SIGMA_MNQ_1",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "sigma" / "ports" / "csharp",
    logic_of=None,
    freqtrade_class="SigmaNetStrategy",
    multicharts_class="SigmaNetSignal",
    multicharts_template="SigmaNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "SigmaNetConfig", "CONFIG_DIR"]
