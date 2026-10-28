"""M2 (MNQ) — METODA 2 na MNQ: tá istá logika ako `m2`, vlastný profil na MNQ.

Variant existuje, aby bola M2 vo webapp aj v priečinku svojho trhu; engine, parametre aj kresby sú predlohy
(`tradebot/strategies/m2`).
"""

from __future__ import annotations

from dataclasses import replace

from ..m2 import SPEC as BASE_SPEC
from .config import CONFIG_DIR, M2MNQConfig

SPEC = replace(
    BASE_SPEC,
    key="m2mnq",
    title="M2 (MNQ)",
    config_cls=M2MNQConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_1m",
    default_timeframe="1m",
    logic_of="m2",  # engine a čítanie polí má predloha
    freqtrade_class="M2MNQStrategy",
    multicharts_class="M2MNQSignal",
    multicharts_template="M2MNQ_Signal.py",
)

__all__ = ["SPEC", "M2MNQConfig", "CONFIG_DIR"]
