"""FLASH TRIGGER ORB 1.0 (ES) — tá istá logika ako `flashorb`, vlastné profily na ES.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na ES
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..flashorb import SPEC as BASE_SPEC
from .config import CONFIG_DIR, FlashorbEsConfig

SPEC = replace(
    BASE_SPEC,
    key="flashorbes",
    title="FLASH TRIGGER ORB 1.0 (ES)",
    config_cls=FlashorbEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_15m",
    logic_of="flashorb",  # engine a čítanie polí má predloha
    freqtrade_class="FlashorbEsStrategy",
    multicharts_class="FlashorbEsSignal",
    multicharts_template="FlashorbEs_Signal.py",
)

__all__ = ["SPEC", "FlashorbEsConfig", "CONFIG_DIR"]
