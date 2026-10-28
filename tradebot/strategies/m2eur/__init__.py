"""M2 (6E) — METODA 2 na Euro FX 6E: tá istá logika ako `m2`, vlastný profil na Euro FX 6E.

Variant existuje, aby bola M2 vo webapp aj v priečinku svojho trhu; engine, parametre aj kresby sú predlohy
(`tradebot/strategies/m2`).
"""

from __future__ import annotations

from dataclasses import replace

from ..m2 import SPEC as BASE_SPEC
from .config import CONFIG_DIR, M2EURConfig

SPEC = replace(
    BASE_SPEC,
    key="m2eur",
    title="M2 (6E)",
    config_cls=M2EURConfig,
    profile_dir=CONFIG_DIR,
    default_profile="6e_databento_1m",
    default_timeframe="1m",
    logic_of="m2",  # engine a čítanie polí má predloha
    freqtrade_class="M2EURStrategy",
    multicharts_class="M2EURSignal",
    multicharts_template="M2EUR_Signal.py",
)

__all__ = ["SPEC", "M2EURConfig", "CONFIG_DIR"]
