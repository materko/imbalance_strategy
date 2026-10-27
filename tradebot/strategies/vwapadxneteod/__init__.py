"""VWAP ADX Pullback (C# jadro EOD) — VWAP ADX Pullback s jadrom v C# a koncom obchodného dňa pre prop účty.

Tá istá stratégia ako `vwapadxnet` (VWAP ADX Pullback (C# jadro)), len o 15:59 New York (21:59 nášho času) zavrie všetky otvorené pozície, zruší čakajúce príkazy a do 18:00 New York (nový obchodný deň CME) nevstúpi. Pozícia teda nikdy neprežije
koniec obchodného dňa, ako to chcú prop firmy na futures. Okno je vždy v čase New York: aj v týždňoch, keď sa letný čas
v USA a v Európe mení v iný deň, sa zatvára o 15:59 NY (u nás vtedy 20:59), nikdy nie neskôr.

Logiku robí C# obal `EodCloseEngine` (`tradebot/core/ports/csharp/TradeBot.Core/EodClose.cs`) nad enginom predlohy; trieda s kľúčom
`vwapadxneteod` je v `tradebot/strategies/vwapadx/ports/csharp`. Mimo okna EOD sú ordery a kresby bit po bite tie isté ako pri `vwapadxnet`
(`tester/tests/test_csharp_eod.py`). Parametre, profily a kresby sú zhodné s predlohou.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..vwapadxnet import SPEC as BASE_SPEC
from .config import CONFIG_DIR, VwapAdxNetEodConfig

#: Kľúč C# enginu — `[TradeBotEngine("vwapadxneteod", ...)]`.
CSHARP_KEY = "vwapadxneteod"

SPEC = replace(
    BASE_SPEC,
    key="vwapadxneteod",
    title="VWAP ADX Pullback (C# jadro EOD)",
    config_cls=VwapAdxNetEodConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_1m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="VwapAdxNetEodStrategy",
    multicharts_class="VwapAdxNetEodSignal",
    multicharts_template="VwapAdxNetEod_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "VwapAdxNetEodConfig", "CONFIG_DIR"]
