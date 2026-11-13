"""Silver Bullet 1.0 (BTC) — tá istá logika ako `silverbullet`, vlastné profily na BTCUSDT.P (Binance futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (BTC) a smernica ju ladila na BTCUSDT.P
(Binance futures) odznova (používateľ 13. 11. 2026: štúdium grafu BTC — najživšie otvorenie New Yorku, krátke TF sa
vracajú, poplatok burzy chce väčší pohyb na obchod); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..silverbullet import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SilverBulletBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="silverbulletbtc",
    title="Silver Bullet 1.0 (BTC)",
    config_cls=SilverBulletBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_5m",
    logic_of="silverbullet",  # engine a čítanie polí má predloha
    freqtrade_class="SilverBulletBtcStrategy",
    multicharts_class="SilverBulletBtcSignal",
    multicharts_template="SilverBulletBtc_Signal.py",
)

__all__ = ["SPEC", "SilverBulletBtcConfig", "CONFIG_DIR"]
