"""IBS EZ MYM (C# jadro) — IBS EZ MYM s jadrom v C#, aby bežala naživo v NinjaTraderi a MetaTraderi 5 na MYM / YM.

Logika je C# jadro IBS Entry Zone (`tradebot/strategies/ibsentry/ports/csharp`, kľúč `ibsentrymymnet` na triede
`IbsEntryMymEngine`) s filtrom trendu / volatility z `EntryLayers` — to isté, čo Python `ibsentrymym`. Ladenie a smernica
na MYM bežia od 12. 11. 2026; prešlé profily pribudnú sem. Zhodu s Python predlohou na MYM stráži
`tester/tests/test_csharp_parity_mym.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.entry_filter import entry_filter_params

from ..ibsentrynet import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IBSEntryMymNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("ibsentrymymnet", ...)]`.
CSHARP_KEY = "ibsentrymymnet"
_GF = "🧭 Filter trendu a volatility (len MYM)"

SPEC = replace(
    BASE_SPEC,
    key="ibsentrymymnet",
    base_key="ibsentrymym",
    title="IBS EZ MYM (C# jadro)",
    config_cls=IBSEntryMymNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_3m",
    param_meta={**BASE_SPEC.param_meta, **entry_filter_params(_GF)},
    param_groups=(*BASE_SPEC.param_groups, _GF),
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="IBSEntryMymNetStrategy",
    multicharts_class="IBSEntryMymNetSignal",
    multicharts_template="IBSEntryMymNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "IBSEntryMymNetConfig", "CONFIG_DIR"]
