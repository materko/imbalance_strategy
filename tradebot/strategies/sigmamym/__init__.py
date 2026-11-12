"""SIGMA BREAKOUT 1.0 (MYM) — tá istá logika ako `sigma`, vlastné profily na MYM.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju ladila na MYM odznova
(používateľ 12. 11. 2026: stratégie na Micro Dow ladiť na MYM odznova); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..sigma import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SigmaMymConfig

SPEC = replace(
    BASE_SPEC,
    key="sigmamym",
    title="SIGMA BREAKOUT 1.0 (MYM)",
    config_cls=SigmaMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_5m",
    logic_of="sigma",  # engine a čítanie polí má predloha
    freqtrade_class="SigmaMymStrategy",
    multicharts_class="SigmaMymSignal",
    multicharts_template="SigmaMym_Signal.py",
)

__all__ = ["SPEC", "SigmaMymConfig", "CONFIG_DIR"]
