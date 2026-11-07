"""SIGMA BREAKOUT 1.0 MGC (C# jadro) — `sigmamgc` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/sigmamgc` do C# (`tradebot/strategies/sigma/ports/csharp`, kľúč `sigmamgcnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Profily `PRESIEL_SMERNICAMI_SIGMA_MGC_*` prešli smernicou (trieda A auditu
7. 11. 2026, Sortino ≥ 2). Zhodu s Python predlohou `sigmamgc` bar po bare stráži `tester/tests/test_csharp_parity_sigmamgcnet.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..sigmamgc import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SigmaMgcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("sigmamgcnet", ...)]`.
CSHARP_KEY = "sigmamgcnet"

SPEC = replace(
    BASE_SPEC,
    key="sigmamgcnet",
    title="SIGMA BREAKOUT 1.0 MGC (C# jadro)",
    config_cls=SigmaMgcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="PRESIEL_SMERNICAMI_SIGMA_MGC_1",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "sigma" / "ports" / "csharp",
    logic_of=None,
    freqtrade_class="SigmaMgcNetStrategy",
    multicharts_class="SigmaMgcNetSignal",
    multicharts_template="SigmaMgcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "SigmaMgcNetConfig", "CONFIG_DIR"]
