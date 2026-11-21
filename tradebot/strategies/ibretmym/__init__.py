"""IB RETRACE 1.0 (MYM) — tá istá logika ako `ibret`, vlastné profily na Micro Dow.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju ladila na MYM odznova
(používateľ 21. 11. 2026: IB RETRACE na zlate, MNQ a MYM). Úrovne sú zlomky šírky IB, takže sa trhu prispôsobia
samy; engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..ibret import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IbRetMymConfig

SPEC = replace(
    BASE_SPEC,
    key="ibretmym",
    title="IB RETRACE 1.0 (MYM)",
    config_cls=IbRetMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_5m",
    logic_of="ibret",  # engine a čítanie polí má predloha
    freqtrade_class="IbRetMymStrategy",
    multicharts_class="IbRetMymSignal",
    multicharts_template="IbRetMym_Signal.py",
)

__all__ = ["SPEC", "IbRetMymConfig", "CONFIG_DIR"]
