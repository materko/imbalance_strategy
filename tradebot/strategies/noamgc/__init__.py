"""NOA 1.0 (MGC) — tá istá logika ako `noa`, vlastné profily na MGC.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju testovala na MGC
(používateľ 11. 11. 2026: NOA ako na Nasdaqu aj na MGC a ES); engine, parametre aj kresby sú predlohy.
Pásmo šumu a poistka sú v percentách z ceny, takže sa trhu prispôsobia samy.
"""

from __future__ import annotations

from dataclasses import replace

from ..noa import SPEC as BASE_SPEC
from .config import CONFIG_DIR, NoaMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="noamgc",
    title="NOA 1.0 (MGC)",
    config_cls=NoaMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    logic_of="noa",  # engine a čítanie polí má predloha
    freqtrade_class="NoaMgcStrategy",
    multicharts_class="NoaMgcSignal",
    multicharts_template="NoaMgc_Signal.py",
)

__all__ = ["SPEC", "NoaMgcConfig", "CONFIG_DIR"]
