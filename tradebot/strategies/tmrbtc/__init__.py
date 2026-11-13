"""T-MEAN REVERSION 1.0 (BTC) — tá istá logika ako `tmr`, vlastné profily na BTCUSDT.P (Binance futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (BTC) a smernica ju ladila na BTCUSDT.P
(Binance futures) odznova (používateľ 13. 11. 2026: štúdium grafu BTC — najživšie otvorenie New Yorku, krátke TF sa
vracajú, poplatok burzy chce väčší pohyb na obchod); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..tmr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, TmrBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="tmrbtc",
    title="T-MEAN REVERSION 1.0 (BTC)",
    config_cls=TmrBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_15m",
    logic_of="tmr",  # engine a čítanie polí má predloha
    freqtrade_class="TmrBtcStrategy",
    multicharts_class="TmrBtcSignal",
    multicharts_template="TmrBtc_Signal.py",
)

__all__ = ["SPEC", "TmrBtcConfig", "CONFIG_DIR"]
