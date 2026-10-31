"""NQ PRECISION 1.0 (ES) — tá istá logika ako `nqprec`, vlastné profily na ES.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na ES
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..nqprec import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NqprecEsConfig

SPEC = replace(
    BASE_SPEC,
    key="nqpreces",
    title="NQ PRECISION 1.0 (ES)",
    config_cls=NqprecEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_1m",
    logic_of="nqprec",  # engine a čítanie polí má predloha
    freqtrade_class="NqprecEsStrategy",
    multicharts_class="NqprecEsSignal",
    multicharts_template="NqprecEs_Signal.py",
)

__all__ = ["SPEC", "NqprecEsConfig", "CONFIG_DIR"]
