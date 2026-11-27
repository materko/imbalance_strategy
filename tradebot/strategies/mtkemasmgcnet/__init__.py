"""MTK EMAS 1.0 MGC (C# jadro) — `mtkemasmgc` s jadrom v C# (`tradebot/strategies/mtkemas/ports/csharp`, kľúč `mtkemasmgcnet`)."""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..mtkemasnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, MtkEmasMgcNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("mtkemasmgcnet", ...)]`.
CSHARP_KEY = "mtkemasmgcnet"

SPEC = replace(
    NET_SPEC,
    key="mtkemasmgcnet",
    base_key="mtkemasmgc",
    title="MTK EMAS 1.0 MGC (C# jadro)",
    config_cls=MtkEmasMgcNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_MGC",
    default_timeframe="4h",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="MtkEmasMgcNetStrategy",
    multicharts_class="MtkEmasMgcNetSignal",
    multicharts_template="MtkEmasMgcNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "MtkEmasMgcNetConfig", "CONFIG_DIR"]
