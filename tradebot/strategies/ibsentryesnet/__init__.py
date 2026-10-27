"""IBS EZ ES (C# jadro) — IBS EZ ES s jadrom v C#, aby bežala naživo v NinjaTraderi a MetaTraderi 5 na ES / MES.

Logika je C# jadro IBS Entry Zone (`tradebot/csharp/TradeBot.Strategies/IbsEntryNet`, kľúč `ibsentryesnet` na triede
`IbsEntryEsEngine`) s filtrom trendu / volatility z `EntryLayers` — to isté, čo Python `ibsentryes`. Profil
`PRESIEL_SMERNICAMI_IBS_EZ_ES_1` prešiel smernicou (25. 10. 2026, kroky 1–8, prahy v násobkoch ATR).
Zhodu s Python predlohou na ES stráži `tester/tests/test_csharp_parity_es.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.entry_filter import entry_filter_params

from ..ibsentrynet import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IBSEntryEsNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("ibsentryesnet", ...)]`.
CSHARP_KEY = "ibsentryesnet"
_GF = "🧭 Filter trendu a volatility (len ES)"

SPEC = replace(
    BASE_SPEC,
    key="ibsentryesnet",
    title="IBS EZ ES (C# jadro)",
    config_cls=IBSEntryEsNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="PRESIEL_SMERNICAMI_IBS_EZ_ES_1",
    param_meta={**BASE_SPEC.param_meta, **entry_filter_params(_GF)},
    param_groups=(*BASE_SPEC.param_groups, _GF),
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="IBSEntryEsNetStrategy",
    multicharts_class="IBSEntryEsNetSignal",
    multicharts_template="IBSEntryEsNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "IBSEntryEsNetConfig", "CONFIG_DIR"]
