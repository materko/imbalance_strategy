"""M2 (MGC) — METODA 2 na MGC: tá istá logika ako `m2`, vlastný profil na MGC.

Variant existuje, aby bola M2 vo webapp aj v priečinku svojho trhu; engine, parametre aj kresby sú predlohy
(`tradebot/strategies/m2`).
"""

from __future__ import annotations

from dataclasses import replace

from ..m2 import SPEC as BASE_SPEC
from .config import CONFIG_DIR, M2MGCConfig

SPEC = replace(
    BASE_SPEC,
    key="m2mgc",
    title="M2 (MGC)",
    config_cls=M2MGCConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_1m",
    default_timeframe="1m",
    logic_of="m2",  # engine a čítanie polí má predloha
    freqtrade_class="M2MGCStrategy",
    multicharts_class="M2MGCSignal",
    multicharts_template="M2MGC_Signal.py",
)

__all__ = ["SPEC", "M2MGCConfig", "CONFIG_DIR"]
