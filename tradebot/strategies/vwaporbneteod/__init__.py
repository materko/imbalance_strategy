"""VWAP ORB 1.5 (C# jadro EOD) — VWAP ORB 1.5 s jadrom v C# a koncom obchodného dňa pre prop účty.

Tá istá stratégia ako `vwaporbnet` (VWAP ORB 1.5 (C# jadro)), len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi. Pozícia teda nikdy neprežije
koniec obchodného dňa, ako to chcú prop firmy na futures. Okno je vždy v čase New York: aj v týždňoch, keď sa letný čas
v USA a v Európe mení v iný deň, sa zatvára o 15:59 NY (u nás vtedy 20:59), nikdy nie neskôr.

Logiku robí C# obal `EodCloseEngine` (`tradebot/csharp/TradeBot.Core/EodClose.cs`) nad enginom predlohy; trieda s kľúčom
`vwaporbneteod` je v `tradebot/csharp/TradeBot.Strategies/VwapOrbNet`. Mimo okna EOD sú ordery a kresby bit po bite tie isté ako pri `vwaporbnet`
(`tester/tests/test_csharp_eod.py`). Parametre, profily a kresby sú zhodné s predlohou.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..vwaporbnet import SPEC as BASE_SPEC
from .config import CONFIG_DIR, VwapOrbNetEodConfig

#: Kľúč C# enginu — `[TradeBotEngine("vwaporbneteod", ...)]`.
CSHARP_KEY = "vwaporbneteod"

SPEC = replace(
    BASE_SPEC,
    key="vwaporbneteod",
    title="VWAP ORB 1.5 (C# jadro EOD)",
    config_cls=VwapOrbNetEodConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="VwapOrbNetEodStrategy",
    multicharts_class="VwapOrbNetEodSignal",
    multicharts_template="VwapOrbNetEod_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "VwapOrbNetEodConfig", "CONFIG_DIR"]
