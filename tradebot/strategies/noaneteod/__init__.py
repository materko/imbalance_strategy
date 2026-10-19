"""NOA 1.0 (C# jadro EOD) — NOA 1.0 s jadrom v C# a koncom obchodného dňa pre prop účty.

Tá istá stratégia ako `noanet` (NOA 1.0 (C# jadro)), len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi. Pozícia teda nikdy neprežije
koniec obchodného dňa, ako to chcú prop firmy na futures. Okno je vždy v čase New York: aj v týždňoch, keď sa letný čas
v USA a v Európe mení v iný deň, sa zatvára o 15:59 NY (u nás vtedy 20:59), nikdy nie neskôr.

Logiku robí C# obal `EodCloseEngine` (`csharp/TradeBot.Core/EodClose.cs`) nad enginom predlohy; trieda s kľúčom
`noaneteod` je v `csharp/TradeBot.Strategies/NoaNet`. Mimo okna EOD sú ordery a kresby bit po bite tie isté ako pri `noanet`
(`tester/tests/test_csharp_eod.py`). Parametre, profily a kresby sú zhodné s predlohou.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..noanet import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NoaNetEodConfig

#: Kľúč C# enginu — `[TradeBotEngine("noaneteod", ...)]`.
CSHARP_KEY = "noaneteod"

SPEC = replace(
    BASE_SPEC,
    key="noaneteod",
    title="NOA 1.0 (C# jadro EOD)",
    config_cls=NoaNetEodConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="NoaNetEodStrategy",
    multicharts_class="NoaNetEodSignal",
    multicharts_template="NoaNetEod_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "NoaNetEodConfig", "CONFIG_DIR"]
