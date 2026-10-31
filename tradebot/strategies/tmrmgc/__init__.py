"""T-MEAN REVERSION 1.0 (MGC) — tá istá logika ako `tmr`, vlastné profily na MGC.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MGC
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..tmr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, TmrMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="tmrmgc",
    title="T-MEAN REVERSION 1.0 (MGC)",
    config_cls=TmrMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_15m",
    logic_of="tmr",  # engine a čítanie polí má predloha
    freqtrade_class="TmrMgcStrategy",
    multicharts_class="TmrMgcSignal",
    multicharts_template="TmrMgc_Signal.py",
)

__all__ = ["SPEC", "TmrMgcConfig", "CONFIG_DIR"]
