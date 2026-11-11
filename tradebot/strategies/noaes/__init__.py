"""NOA 1.0 (ES) — tá istá logika ako `noa`, vlastné profily na ES.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na ES
(používateľ 11. 11. 2026: NOA ako na Nasdaqu aj na MGC a ES); engine, parametre aj kresby sú predlohy.
Pásmo šumu a poistka sú v percentách z ceny, takže sa trhu prispôsobia samy.
"""

from __future__ import annotations

from dataclasses import replace

from ..noa import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NoaEsConfig

SPEC = replace(
    BASE_SPEC,
    key="noaes",
    title="NOA 1.0 (ES)",
    config_cls=NoaEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="es_databento_5m",
    logic_of="noa",  # engine a čítanie polí má predloha
    freqtrade_class="NoaEsStrategy",
    multicharts_class="NoaEsSignal",
    multicharts_template="NoaEs_Signal.py",
)

__all__ = ["SPEC", "NoaEsConfig", "CONFIG_DIR"]
