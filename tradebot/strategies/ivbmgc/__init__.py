"""IVB 1.0 (MGC) — tá istá logika ako `ivb`, vlastné profily na MGC.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MGC
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..ivb import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IvbMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="ivbmgc",
    title="IVB 1.0 (MGC)",
    config_cls=IvbMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    logic_of="ivb",  # engine a čítanie polí má predloha
    freqtrade_class="IvbMgcStrategy",
    multicharts_class="IvbMgcSignal",
    multicharts_template="IvbMgc_Signal.py",
)

__all__ = ["SPEC", "IvbMgcConfig", "CONFIG_DIR"]
