"""NY VA BREAKOUT ES — NY VA BREAKOUT 1.0 na S&P 500 futures (ES).

Tá istá logika ako `nyva` (engine, config, kresby a vrstvy sa preberajú bez zmeny); vlastné sú profily (`configs/`).
Bodové prahy (max stop, šírka VA) sú na ES asi 4,5× menšie ako na NQ. Stratégia na NQ sa nemení.
"""

from __future__ import annotations

from dataclasses import replace

from ..nyva import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NyVaEsConfig

SPEC = replace(
    BASE_SPEC,
    key="nyvaes",
    title="NY VA BREAKOUT ES",
    config_cls=NyVaEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_3m",
    logic_of="nyva",
    freqtrade_class="NyVaEsStrategy",
    multicharts_class="NyVaEsSignal",
    multicharts_template="NyVaEs_Signal.py",
)

__all__ = ["SPEC", "NyVaEsConfig", "CONFIG_DIR"]
