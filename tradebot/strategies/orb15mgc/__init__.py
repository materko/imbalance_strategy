"""ORB 15/5 1.0 (MGC) — tá istá logika ako `orb15`, vlastné profily na MGC.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MGC
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..orb15 import SPEC as BASE_SPEC
from .config import CONFIG_DIR, Orb15MgcConfig

SPEC = replace(
    BASE_SPEC,
    key="orb15mgc",
    title="ORB 15/5 1.0 (MGC)",
    config_cls=Orb15MgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    logic_of="orb15",  # engine a čítanie polí má predloha
    freqtrade_class="Orb15MgcStrategy",
    multicharts_class="Orb15MgcSignal",
    multicharts_template="Orb15Mgc_Signal.py",
)

__all__ = ["SPEC", "Orb15MgcConfig", "CONFIG_DIR"]
