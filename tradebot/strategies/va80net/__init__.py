"""MTK RANGE 1.0 (C# jadro) — `va80` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/va80` do C# (`tradebot/strategies/va80/ports/csharp`, kľúč `va80net`) s obalmi
vstupov a veľkosti pozície z `EntryLayers`. Profily: zatiaľ profil repozitára predlohy (smernica beží). Zhodu s Python predlohou `va80` bar po bare stráži `tester/tests/test_csharp_parity_va80.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..va80 import SPEC as BASE_SPEC
from .config import CONFIG_DIR, Va80NetConfig

#: Kľúč C# enginu — `[TradeBotEngine("va80net", ...)]`.
CSHARP_KEY = "va80net"

SPEC = replace(
    BASE_SPEC,
    key="va80net",
    title="MTK RANGE 1.0 (C# jadro)",
    config_cls=Va80NetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_1m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "va80" / "ports" / "csharp",
    logic_of=None,
    freqtrade_class="Va80NetStrategy",
    multicharts_class="Va80NetSignal",
    multicharts_template="Va80Net_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "Va80NetConfig", "CONFIG_DIR"]
