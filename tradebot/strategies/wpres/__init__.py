"""WILLIAMS %R LONG 1.0 (ES) — tá istá logika ako `wpr`, vlastné profily na ES.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na ES
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..wpr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, WprEsConfig

SPEC = replace(
    BASE_SPEC,
    key="wpres",
    title="WILLIAMS %R LONG 1.0 (ES)",
    config_cls=WprEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_15m",
    logic_of="wpr",  # engine a čítanie polí má predloha
    freqtrade_class="WprEsStrategy",
    multicharts_class="WprEsSignal",
    multicharts_template="WprEs_Signal.py",
)

__all__ = ["SPEC", "WprEsConfig", "CONFIG_DIR"]
