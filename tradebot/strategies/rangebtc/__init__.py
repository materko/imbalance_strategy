"""Range Breakout (BTC) — tá istá logika ako `range`, vlastné profily na BTCUSDT.P (Binance futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (BTC) a smernica ju ladila na BTCUSDT.P
(Binance futures) odznova (používateľ 13. 11. 2026: štúdium grafu BTC — najživšie otvorenie New Yorku, krátke TF sa
vracajú, poplatok burzy chce väčší pohyb na obchod); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..range import SPEC as BASE_SPEC
from .config import CONFIG_DIR, RangeBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="rangebtc",
    title="Range Breakout (BTC)",
    config_cls=RangeBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_3m",
    logic_of="range",  # engine a čítanie polí má predloha
    freqtrade_class="RangeBtcStrategy",
    multicharts_class="RangeBtcSignal",
    multicharts_template="RangeBtc_Signal.py",
)

__all__ = ["SPEC", "RangeBtcConfig", "CONFIG_DIR"]
