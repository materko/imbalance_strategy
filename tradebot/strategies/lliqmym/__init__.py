"""LONDON LIQUIDITY IFVG 1.0 (MYM) — tá istá logika ako `lliq`, vlastné profily na MYM.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju ladila na MYM odznova
(používateľ 12. 11. 2026: stratégie na Micro Dow ladiť na MYM odznova); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..lliq import SPEC as BASE_SPEC
from .config import CONFIG_DIR, LliqMymConfig

SPEC = replace(
    BASE_SPEC,
    key="lliqmym",
    title="LONDON LIQUIDITY IFVG 1.0 (MYM)",
    config_cls=LliqMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_5m",
    logic_of="lliq",  # engine a čítanie polí má predloha
    freqtrade_class="LliqMymStrategy",
    multicharts_class="LliqMymSignal",
    multicharts_template="LliqMym_Signal.py",
)

__all__ = ["SPEC", "LliqMymConfig", "CONFIG_DIR"]
