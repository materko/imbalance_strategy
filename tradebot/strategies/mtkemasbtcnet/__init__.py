"""MTK EMAS 1.0 BTC (C# jadro) — `mtkemasbtc` s jadrom v C# (`tradebot/strategies/mtkemas/ports/csharp`, kľúč `mtkemasbtcnet`)."""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..mtkemasnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, MtkEmasBtcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("mtkemasbtcnet", ...)]`.
CSHARP_KEY = "mtkemasbtcnet"

SPEC = replace(
    NET_SPEC,
    key="mtkemasbtcnet",
    base_key="mtkemasbtc",
    title="MTK EMAS 1.0 BTC (C# jadro)",
    config_cls=MtkEmasBtcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_BTC",
    default_timeframe="4h",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="MtkEmasBtcNetStrategy",
    multicharts_class="MtkEmasBtcNetSignal",
    multicharts_template="MtkEmasBtcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "MtkEmasBtcNetConfig", "CONFIG_DIR"]
