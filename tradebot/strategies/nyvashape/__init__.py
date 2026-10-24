"""NY VA SHAPE — NY VA BREAKOUT s podmienkou tvaru profilu prvej hodiny (zadanie používateľa 24. 10. 2026).

Prieraz nad VAH len pri **P-profile** (POC a value area v hornej časti rangeu, tenký chvost dole), pod VAL len pri
**b-profile**. Logika je balík `nyva` (`useShape`); táto stratégia má podmienku predvolene zapnutú.
"""

from __future__ import annotations

from dataclasses import replace

from ..nyva import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NyVaShapeConfig

SPEC = replace(
    BASE_SPEC,
    key="nyvashape",
    title="NY VA SHAPE",
    config_cls=NyVaShapeConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_3m",
    logic_of="nyva",
    freqtrade_class="NyVaShapeStrategy",
    multicharts_class="NyVaShapeSignal",
    multicharts_template="NyVaShape_Signal.py",
)

__all__ = ["SPEC", "NyVaShapeConfig", "CONFIG_DIR"]
