"""T-MEAN REVERSION 1.0 (MYM) — tá istá logika ako `tmr`, vlastné profily na MYM.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju ladila na MYM odznova
(používateľ 12. 11. 2026: stratégie na Micro Dow ladiť na MYM odznova); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..tmr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, TmrMymConfig

SPEC = replace(
    BASE_SPEC,
    key="tmrmym",
    title="T-MEAN REVERSION 1.0 (MYM)",
    config_cls=TmrMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_15m",
    logic_of="tmr",  # engine a čítanie polí má predloha
    freqtrade_class="TmrMymStrategy",
    multicharts_class="TmrMymSignal",
    multicharts_template="TmrMym_Signal.py",
)

__all__ = ["SPEC", "TmrMymConfig", "CONFIG_DIR"]
