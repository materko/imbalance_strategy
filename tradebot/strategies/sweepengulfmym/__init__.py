"""SWEEPING ENGULF 1.0 (MYM) — tá istá logika ako `sweepengulf`, vlastné profily na Micro Dow (MYM).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (DOW) a smernica ju ladila na MYM odznova
(používateľ 12. 11. 2026: stratégie na Micro Dow, nastavenia z MNQ / ES sa na MYM neprenášajú); engine, parametre aj kresby
sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..sweepengulf import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SweepEngulfMymConfig

SPEC = replace(
    BASE_SPEC,
    key="sweepengulfmym",
    title="SWEEPING ENGULF 1.0 (MYM)",
    config_cls=SweepEngulfMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_4h",
    logic_of="sweepengulf",  # engine a čítanie polí má predloha
    freqtrade_class="SweepEngulfMymStrategy",
    multicharts_class="SweepEngulfMymSignal",
    multicharts_template="SweepEngulfMym_Signal.py",
)

__all__ = ["SPEC", "SweepEngulfMymConfig", "CONFIG_DIR"]
