"""DAILY OPEN 1.0 (BTC) — tá istá logika ako `dailyopen`, vlastné profily na BTCUSDT.P (Binance futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (BTC) a smernica ju ladila na BTCUSDT.P
(Binance futures) odznova (používateľ 13. 11. 2026: štúdium grafu BTC — najživšie otvorenie New Yorku, krátke TF sa
vracajú, poplatok burzy chce väčší pohyb na obchod); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..dailyopen import SPEC as BASE_SPEC
from .config import CONFIG_DIR, DailyOpenBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="dailyopenbtc",
    title="DAILY OPEN 1.0 (BTC)",
    config_cls=DailyOpenBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_1h",
    logic_of="dailyopen",  # engine a čítanie polí má predloha
    freqtrade_class="DailyOpenBtcStrategy",
    multicharts_class="DailyOpenBtcSignal",
    multicharts_template="DailyOpenBtc_Signal.py",
)

__all__ = ["SPEC", "DailyOpenBtcConfig", "CONFIG_DIR"]
