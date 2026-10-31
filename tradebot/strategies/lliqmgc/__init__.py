"""LONDON LIQUIDITY IFVG 1.0 (MGC) — tá istá logika ako `lliq`, vlastné profily na MGC.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MGC
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..lliq import SPEC as BASE_SPEC
from .config import CONFIG_DIR, LliqMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="lliqmgc",
    title="LONDON LIQUIDITY IFVG 1.0 (MGC)",
    config_cls=LliqMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    logic_of="lliq",  # engine a čítanie polí má predloha
    freqtrade_class="LliqMgcStrategy",
    multicharts_class="LliqMgcSignal",
    multicharts_template="LliqMgc_Signal.py",
)

__all__ = ["SPEC", "LliqMgcConfig", "CONFIG_DIR"]
