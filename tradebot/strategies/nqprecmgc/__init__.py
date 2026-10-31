"""NQ PRECISION 1.0 (MGC) — tá istá logika ako `nqprec`, vlastné profily na MGC.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MGC
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..nqprec import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NqprecMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="nqprecmgc",
    title="NQ PRECISION 1.0 (MGC)",
    config_cls=NqprecMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_1m",
    logic_of="nqprec",  # engine a čítanie polí má predloha
    freqtrade_class="NqprecMgcStrategy",
    multicharts_class="NqprecMgcSignal",
    multicharts_template="NqprecMgc_Signal.py",
)

__all__ = ["SPEC", "NqprecMgcConfig", "CONFIG_DIR"]
