"""FLASH TRIGGER ORB 1.0 (BTC) — tá istá logika ako `flashorb`, vlastné profily na BTCUSDT.P (Binance futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (BTC) a smernica ju ladila na BTCUSDT.P
(Binance futures) odznova (používateľ 13. 11. 2026: štúdium grafu BTC — najživšie otvorenie New Yorku, krátke TF sa
vracajú, poplatok burzy chce väčší pohyb na obchod); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..flashorb import SPEC as BASE_SPEC
from .config import CONFIG_DIR, FlashorbBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="flashorbbtc",
    title="FLASH TRIGGER ORB 1.0 (BTC)",
    config_cls=FlashorbBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_15m",
    logic_of="flashorb",  # engine a čítanie polí má predloha
    freqtrade_class="FlashorbBtcStrategy",
    multicharts_class="FlashorbBtcSignal",
    multicharts_template="FlashorbBtc_Signal.py",
)

__all__ = ["SPEC", "FlashorbBtcConfig", "CONFIG_DIR"]
