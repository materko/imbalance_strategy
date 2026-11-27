"""MTK EMAS 1.0 MYM (C# jadro) — `mtkemasmym` s jadrom v C# (`tradebot/strategies/mtkemas/ports/csharp`, kľúč `mtkemasmymnet`)."""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..mtkemasnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, MtkEmasMymNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("mtkemasmymnet", ...)]`.
CSHARP_KEY = "mtkemasmymnet"

SPEC = replace(
    NET_SPEC,
    key="mtkemasmymnet",
    base_key="mtkemasmym",
    title="MTK EMAS 1.0 MYM (C# jadro)",
    config_cls=MtkEmasMymNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_MYM",
    default_timeframe="2h",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="MtkEmasMymNetStrategy",
    multicharts_class="MtkEmasMymNetSignal",
    multicharts_template="MtkEmasMymNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "MtkEmasMymNetConfig", "CONFIG_DIR"]
