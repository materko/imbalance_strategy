"""ORB 15/5 1.0 (ES) — tá istá logika ako `orb15`, vlastné profily na ES.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na ES
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..orb15 import SPEC as BASE_SPEC
from .config import CONFIG_DIR, Orb15EsConfig

SPEC = replace(
    BASE_SPEC,
    key="orb15es",
    title="ORB 15/5 1.0 (ES)",
    config_cls=Orb15EsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_5m",
    logic_of="orb15",  # engine a čítanie polí má predloha
    freqtrade_class="Orb15EsStrategy",
    multicharts_class="Orb15EsSignal",
    multicharts_template="Orb15Es_Signal.py",
)

__all__ = ["SPEC", "Orb15EsConfig", "CONFIG_DIR"]
