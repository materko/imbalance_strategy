"""NY VA BREAKOUT ES (C# jadro) — NY VA BREAKOUT ES s jadrom v C#, aby bežala naživo v NinjaTraderi a MT5 na ES / MES.

Logika je prepis `tradebot/strategies/nyva` do C# (`csharp/TradeBot.Strategies/NyVaNet`, kľúč `nyvaesnet`) s obalmi
vstupov z `EntryLayers` (trend, potvrdenie pin barom / imbalance, limitka). Profily `PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1–5`
prešli smernicou na ES (25. 10. 2026, kroky 1–7; US500 v kroku 8 nie — len futures). Zhodu s Python predlohou
`nyvaes` bar po bare stráži `tester/tests/test_csharp_parity_es.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import CSHARP_DIR

from ..nyvaes import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NyVaEsNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("nyvaesnet", ...)]` na triede `NyVaEngine`.
CSHARP_KEY = "nyvaesnet"

SPEC = replace(
    BASE_SPEC,
    key="nyvaesnet",
    title="NY VA BREAKOUT ES (C# jadro)",
    config_cls=NyVaEsNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=CSHARP_DIR / "TradeBot.Strategies" / "NyVaNet",
    freqtrade_class="NyVaEsNetStrategy",
    multicharts_class="NyVaEsNetSignal",
    multicharts_template="NyVaEsNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "NyVaEsNetConfig", "CONFIG_DIR"]
