"""IVB 1.0 (ES) — tá istá logika ako `ivb`, vlastné profily na ES.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na ES
(zadanie týždňa 31. 10. 2026: všetky roboquant stratégie na MNQ, ES a MGC); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..ivb import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IvbEsConfig

SPEC = replace(
    BASE_SPEC,
    key="ivbes",
    title="IVB 1.0 (ES)",
    config_cls=IvbEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_5m",
    logic_of="ivb",  # engine a čítanie polí má predloha
    freqtrade_class="IvbEsStrategy",
    multicharts_class="IvbEsSignal",
    multicharts_template="IvbEs_Signal.py",
)

__all__ = ["SPEC", "IvbEsConfig", "CONFIG_DIR"]
