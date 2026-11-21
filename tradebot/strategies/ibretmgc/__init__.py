"""IB RETRACE 1.0 (MGC) — tá istá logika ako `ibret`, vlastné profily na zlato.

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju ladila na MGC odznova
(používateľ 21. 11. 2026: IB RETRACE na zlate, MNQ a MYM). Úrovne sú zlomky šírky IB, takže sa trhu prispôsobia
samy; engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..ibret import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IbRetMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="ibretmgc",
    title="IB RETRACE 1.0 (MGC)",
    config_cls=IbRetMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    logic_of="ibret",  # engine a čítanie polí má predloha
    freqtrade_class="IbRetMgcStrategy",
    multicharts_class="IbRetMgcSignal",
    multicharts_template="IbRetMgc_Signal.py",
)

__all__ = ["SPEC", "IbRetMgcConfig", "CONFIG_DIR"]
