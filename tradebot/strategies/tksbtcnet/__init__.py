"""TKS 1.0 BTC (C# jadro) — `tksbtc` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/tks` do C# (`tradebot/strategies/tks/ports/csharp`, kľúč `tksbtcnet`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Zhodu s Python predlohou `tksbtc` bar po bare stráži
`tester/tests/test_csharp_parity_tks.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..tksnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, TksBtcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("tksbtcnet", ...)]`.
CSHARP_KEY = "tksbtcnet"

SPEC = replace(
    NET_SPEC,
    key="tksbtcnet",
    base_key="tksbtc",
    title="TKS 1.0 BTC (C# jadro)",
    config_cls=TksBtcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_3m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="TksBtcNetStrategy",
    multicharts_class="TksBtcNetSignal",
    multicharts_template="TksBtcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "TksBtcNetConfig", "CONFIG_DIR"]
