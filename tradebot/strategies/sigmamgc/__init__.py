"""SIGMA BREAKOUT 1.0 (MGC) — tá istá logika ako `sigma`, vlastné profily na MGC.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MGC
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..sigma import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SigmaMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="sigmamgc",
    title="SIGMA BREAKOUT 1.0 (MGC)",
    config_cls=SigmaMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    logic_of="sigma",  # engine a čítanie polí má predloha
    freqtrade_class="SigmaMgcStrategy",
    multicharts_class="SigmaMgcSignal",
    multicharts_template="SigmaMgc_Signal.py",
)

__all__ = ["SPEC", "SigmaMgcConfig", "CONFIG_DIR"]
