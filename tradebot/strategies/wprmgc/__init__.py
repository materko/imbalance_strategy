"""WILLIAMS %R LONG 1.0 (MGC) — tá istá logika ako `wpr`, vlastné profily na MGC.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MGC
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..wpr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, WprMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="wprmgc",
    title="WILLIAMS %R LONG 1.0 (MGC)",
    config_cls=WprMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_15m",
    logic_of="wpr",  # engine a čítanie polí má predloha
    freqtrade_class="WprMgcStrategy",
    multicharts_class="WprMgcSignal",
    multicharts_template="WprMgc_Signal.py",
)

__all__ = ["SPEC", "WprMgcConfig", "CONFIG_DIR"]
