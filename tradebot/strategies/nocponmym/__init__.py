"""NOC + PONDELOK 1.0 (MYM) — tá istá logika ako `nocpon`, vlastné profily na Micro Dow (MYM).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (DOW) a smernica ju ladila na MYM odznova
(používateľ 12. 11. 2026: stratégie na Micro Dow, nastavenia z MNQ / ES sa na MYM neprenášajú); engine, parametre aj kresby
sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..nocpon import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NocPonMymConfig

SPEC = replace(
    BASE_SPEC,
    key="nocponmym",
    title="NOC + PONDELOK 1.0 (MYM)",
    config_cls=NocPonMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_5m",
    logic_of="nocpon",  # engine a čítanie polí má predloha
    freqtrade_class="NocPonMymStrategy",
    multicharts_class="NocPonMymSignal",
    multicharts_template="NocPonMym_Signal.py",
)

__all__ = ["SPEC", "NocPonMymConfig", "CONFIG_DIR"]
