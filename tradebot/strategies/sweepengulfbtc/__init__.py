"""SWEEPING ENGULF 1.0 (BTC) — tá istá logika ako `sweepengulf`, vlastné profily na BTCUSDT.P (Binance futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (BTC) a smernica ju ladila na BTCUSDT.P
(Binance futures) odznova (používateľ 13. 11. 2026: štúdium grafu BTC — najživšie otvorenie New Yorku, krátke TF sa
vracajú, poplatok burzy chce väčší pohyb na obchod); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..sweepengulf import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SweepEngulfBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="sweepengulfbtc",
    title="SWEEPING ENGULF 1.0 (BTC)",
    config_cls=SweepEngulfBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_4h",
    logic_of="sweepengulf",  # engine a čítanie polí má predloha
    freqtrade_class="SweepEngulfBtcStrategy",
    multicharts_class="SweepEngulfBtcSignal",
    multicharts_template="SweepEngulfBtc_Signal.py",
)

__all__ = ["SPEC", "SweepEngulfBtcConfig", "CONFIG_DIR"]
