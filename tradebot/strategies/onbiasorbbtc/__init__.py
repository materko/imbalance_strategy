"""Overnight Bias ORB (BTC) — tá istá logika ako `onbiasorb`, vlastné profily na BTCUSDT.P (Binance futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (BTC) a smernica ju ladila na BTCUSDT.P
(Binance futures) odznova (používateľ 13. 11. 2026: štúdium grafu BTC — najživšie otvorenie New Yorku, krátke TF sa
vracajú, poplatok burzy chce väčší pohyb na obchod); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..onbiasorb import SPEC as BASE_SPEC
from .config import CONFIG_DIR, OnBiasOrbBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="onbiasorbbtc",
    title="Overnight Bias ORB (BTC)",
    config_cls=OnBiasOrbBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_15m",
    logic_of="onbiasorb",  # engine a čítanie polí má predloha
    freqtrade_class="OnBiasOrbBtcStrategy",
    multicharts_class="OnBiasOrbBtcSignal",
    multicharts_template="OnBiasOrbBtc_Signal.py",
)

__all__ = ["SPEC", "OnBiasOrbBtcConfig", "CONFIG_DIR"]
