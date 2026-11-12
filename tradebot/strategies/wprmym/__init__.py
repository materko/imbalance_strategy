"""WILLIAMS %R LONG 1.0 (MYM) — tá istá logika ako `wpr`, vlastné profily na MYM.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju ladila na MYM odznova
(používateľ 12. 11. 2026: stratégie na Micro Dow ladiť na MYM odznova); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..wpr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, WprMymConfig

SPEC = replace(
    BASE_SPEC,
    key="wprmym",
    title="WILLIAMS %R LONG 1.0 (MYM)",
    config_cls=WprMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_15m",
    logic_of="wpr",  # engine a čítanie polí má predloha
    freqtrade_class="WprMymStrategy",
    multicharts_class="WprMymSignal",
    multicharts_template="WprMym_Signal.py",
)

__all__ = ["SPEC", "WprMymConfig", "CONFIG_DIR"]
