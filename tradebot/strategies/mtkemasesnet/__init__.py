"""MTK EMAS 1.0 ES (C# jadro) — `mtkemases` s jadrom v C# (`tradebot/strategies/mtkemas/ports/csharp`, kľúč `mtkemasesnet`)."""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..mtkemasnet import SPEC as NET_SPEC
from .config import CONFIG_DIR, MtkEmasEsNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("mtkemasesnet", ...)]`.
CSHARP_KEY = "mtkemasesnet"

SPEC = replace(
    NET_SPEC,
    key="mtkemasesnet",
    base_key="mtkemases",
    title="MTK EMAS 1.0 ES (C# jadro)",
    config_cls=MtkEmasEsNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_1h",
    default_timeframe="1h",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="MtkEmasEsNetStrategy",
    multicharts_class="MtkEmasEsNetSignal",
    multicharts_template="MtkEmasEsNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "MtkEmasEsNetConfig", "CONFIG_DIR"]
