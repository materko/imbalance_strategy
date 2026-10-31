"""SIGMA BREAKOUT 1.0 (ES) — tá istá logika ako `sigma`, vlastné profily na ES.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na ES
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..sigma import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SigmaEsConfig

SPEC = replace(
    BASE_SPEC,
    key="sigmaes",
    title="SIGMA BREAKOUT 1.0 (ES)",
    config_cls=SigmaEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_5m",
    logic_of="sigma",  # engine a čítanie polí má predloha
    freqtrade_class="SigmaEsStrategy",
    multicharts_class="SigmaEsSignal",
    multicharts_template="SigmaEs_Signal.py",
)

__all__ = ["SPEC", "SigmaEsConfig", "CONFIG_DIR"]
