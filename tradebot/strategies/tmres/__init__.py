"""T-MEAN REVERSION 1.0 (ES) — tá istá logika ako `tmr`, vlastné profily na ES.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na ES
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..tmr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, TmrEsConfig

SPEC = replace(
    BASE_SPEC,
    key="tmres",
    title="T-MEAN REVERSION 1.0 (ES)",
    config_cls=TmrEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_15m",
    logic_of="tmr",  # engine a čítanie polí má predloha
    freqtrade_class="TmrEsStrategy",
    multicharts_class="TmrEsSignal",
    multicharts_template="TmrEs_Signal.py",
)

__all__ = ["SPEC", "TmrEsConfig", "CONFIG_DIR"]
