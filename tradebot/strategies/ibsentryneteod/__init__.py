"""IBS Entry Zone (C# jadro EOD) — IBS Entry Zone s jadrom v C# a koncom obchodného dňa pre prop účty.

Tá istá stratégia ako `ibsentrynet` (IBS Entry Zone (C# jadro)), len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi. Pozícia teda nikdy neprežije
koniec obchodného dňa, ako to chcú prop firmy na futures. Okno je vždy v čase New York: aj v týždňoch, keď sa letný čas
v USA a v Európe mení v iný deň, sa zatvára o 15:59 NY (u nás vtedy 20:59), nikdy nie neskôr.

Logiku robí C# obal `EodCloseEngine` (`tradebot/core/csharp/TradeBot.Core/EodClose.cs`) nad enginom predlohy; trieda s kľúčom
`ibsentryneteod` je v `tradebot/strategies/ibsentry/csharp`. Mimo okna EOD sú ordery a kresby bit po bite tie isté ako pri `ibsentrynet`
(`tester/tests/test_csharp_eod.py`). Parametre, profily a kresby sú zhodné s predlohou.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..ibsentrynet import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IBSEntryNetEodConfig

#: Kľúč C# enginu — `[TradeBotEngine("ibsentryneteod", ...)]`.
CSHARP_KEY = "ibsentryneteod"

SPEC = replace(
    BASE_SPEC,
    key="ibsentryneteod",
    title="IBS Entry Zone (C# jadro EOD)",
    config_cls=IBSEntryNetEodConfig,
    profile_dir=CONFIG_DIR,
    default_profile="golden_binance_btcusdt_3m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="IBSEntryNetEodStrategy",
    multicharts_class="IBSEntryNetEodSignal",
    multicharts_template="IBSEntryNetEod_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "IBSEntryNetEodConfig", "CONFIG_DIR"]
