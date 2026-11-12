"""MTK ORB MGC (C# jadro) — `mtkorb` s jadrom v C#, aby bežala naživo v NinjaTraderi 8 a MetaTraderi 5.

Logika je prepis `tradebot/strategies/orb15` do C# (`tradebot/strategies/orb15/ports/csharp`, kľúč `mtkorbnet`) aj s rozšíreniami
MTK ORB (gapFilter, maxOrWidthMult, firstBreakOnly, entryAtLevel) a obalmi vstupov a veľkosti pozície z `EntryLayers`.
Profily `PRESIEL_SMERNICAMI_MTK_ORB_MGC_*` prešli smernicou (12. 11. 2026, ladenie 2010–2024, odložené 2 roky).
Zhodu s Python predlohou `mtkorb` bar po bare stráži `tester/tests/test_csharp_parity_mtkorb.py`.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.adapters.csharp.engine import csharp_engine_factory
from tradebot.core.paths import STRATEGIES_DIR

from ..mtkorb import SPEC as BASE_SPEC
from .config import CONFIG_DIR, MtkOrbNetConfig

#: Kľúč C# enginu — `[TradeBotEngine("mtkorbnet", ...)]`.
CSHARP_KEY = "mtkorbnet"

SPEC = replace(
    BASE_SPEC,
    key="mtkorbnet",
    base_key="mtkorb",
    title="MTK ORB MGC (C# jadro)",
    config_cls=MtkOrbNetConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    engine_factory=csharp_engine_factory(CSHARP_KEY),
    csharp_dir=STRATEGIES_DIR / "orb15" / "ports" / "csharp",
    logic_of=None,
    freqtrade_class="MtkOrbNetStrategy",
    multicharts_class="MtkOrbNetSignal",
    multicharts_template="MtkOrbNet_Signal.py",
)

__all__ = ["SPEC", "CSHARP_KEY", "MtkOrbNetConfig", "CONFIG_DIR"]
