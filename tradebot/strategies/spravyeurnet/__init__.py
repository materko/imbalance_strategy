"""SPRÁVY EUR/USD (C# jadro) — `spravyeur` s jadrom v C#, aby bežali naživo v NinjaTraderi (6E) a MT5 (EURUSD).

Logika je prepis `tradebot/strategies/spravy` do C# (`tradebot/strategies/spravy/ports/csharp`, kľúč `spravyeurnet`)
s obalmi vstupov z `EntryLayers`; kalendár je ten istý `calendar.json` vygenerovaný do `SpravyCalendar.cs`. Zhodu
s Python predlohou bar po bare stráži `tester/tests/test_csharp_parity_spravy.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory

from ..spravynet import SPEC as NET_SPEC
from .config import CONFIG_DIR, SpravyEurNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("spravyeurnet", ...)]`.
CSHARP_KEY = "spravyeurnet"

SPEC = replace(
    NET_SPEC,
    key="spravyeurnet",
    base_key="spravyeur",
    title="SPRÁVY EUR/USD (C# jadro)",
    config_cls=SpravyEurNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_6E",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    freqtrade_class="SpravyEurNetStrategy",
    multicharts_class="SpravyEurNetSignal",
    multicharts_template="SpravyEurNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "SpravyEurNetConfig", "CONFIG_DIR"]
