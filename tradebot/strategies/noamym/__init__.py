"""NOA 1.0 (MYM) — tá istá logika ako `noa`, vlastné profily na MYM.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MYM
(používateľ 12. 11. 2026: stratégie na Micro Dow ladiť na MYM odznova); engine, parametre aj kresby sú predlohy.
Pásmo šumu a poistka sú v percentách z ceny, takže sa trhu prispôsobia samy.
"""

from __future__ import annotations

from dataclasses import replace

from ..noa import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NoaMymConfig

SPEC = replace(
    BASE_SPEC,
    key="noamym",
    title="NOA 1.0 (MYM)",
    config_cls=NoaMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_5m",
    logic_of="noa",  # engine a čítanie polí má predloha
    freqtrade_class="NoaMymStrategy",
    multicharts_class="NoaMymSignal",
    multicharts_template="NoaMym_Signal.py",
)

__all__ = ["SPEC", "NoaMymConfig", "CONFIG_DIR"]
