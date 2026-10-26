"""Fibo 1.0 MGC (C# jadro) — Fibo 1.0 na zlate (MGC) s jadrom v C#, aby bežala naživo v NinjaTraderi a MT5.

Logika je prepis `tradebot/strategies/fibo` do C# (`csharp/TradeBot.Strategies/FiboNet`, kľúč `fibomgcnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Profily `PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1–10` prešli smernicou na MGC
(kroky 1–8, XAU/USD v kroku 8), riziko 500 $ na obchod. Zhodu s Python predlohou `fibomgc` bar po bare stráži
`tester/tests/test_csharp_parity_mgc.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import CSHARP_DIR

from ..fibomgc import SPEC as BASE_SPEC
from .config import CONFIG_DIR, FiboMgcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("fibomgcnet", ...)]` na triede `FiboEngine`.
CSHARP_KEY = "fibomgcnet"

SPEC = replace(
    BASE_SPEC,
    key="fibomgcnet",
    title="Fibo 1.0 MGC (C# jadro)",
    config_cls=FiboMgcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=CSHARP_DIR / "TradeBot.Strategies" / "FiboNet",
    freqtrade_class="FiboMgcNetStrategy",
    multicharts_class="FiboMgcNetSignal",
    multicharts_template="FiboMgcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "FiboMgcNetConfig", "CONFIG_DIR"]
