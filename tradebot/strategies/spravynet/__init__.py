"""SPRÁVY (C# jadro) — SPRÁVY s jadrom v C#, aby bežali naživo v NinjaTraderi (MGC) a MT5 (XAU).

Logika je prepis `tradebot/strategies/spravy` do C# (`tradebot/strategies/spravy/ports/csharp`, kľúč `spravynet`)
s obalmi vstupov z `EntryLayers`; kalendár správ je ten istý `calendar.json`, vygenerovaný do `SpravyCalendar.cs`.
Zhodu s Python predlohou bar po bare (aj cez posun času USA / SK) stráži `tester/tests/test_csharp_parity_spravy.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..spravy import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SpravyNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("spravynet", ...)]` na triede `SpravyEngine`.
CSHARP_KEY = "spravynet"

SPEC = replace(
    BASE_SPEC,
    key="spravynet",
    title="SPRÁVY 3.0 (C# jadro)",
    config_cls=SpravyNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "spravy" / "ports" / "csharp",
    freqtrade_class="SpravyNetStrategy",
    multicharts_class="SpravyNetSignal",
    multicharts_template="SpravyNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "SpravyNetConfig", "CONFIG_DIR"]
