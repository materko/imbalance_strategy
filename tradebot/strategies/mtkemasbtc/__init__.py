"""MTK EMAS 1.0 (BTC) — tá istá logika ako `mtkemas`, vlastné profily na BTC zo štúdie Mac mini (iCloud KLZAKY-STUDIA)."""

from __future__ import annotations

from dataclasses import replace

from ..mtkemas import SPEC as BASE_SPEC
from .config import CONFIG_DIR, MtkEmasBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="mtkemasbtc",
    title="MTK EMAS 1.0 (BTC)",
    config_cls=MtkEmasBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="btcusdt_binance_4h",
    default_timeframe="4h",
    logic_of="mtkemas",  # engine a čítanie polí má predloha
    freqtrade_class="MtkEmasBtcStrategy",
    multicharts_class="MtkEmasBtcSignal",
    multicharts_template="MtkEmasBtc_Signal.py",
)

__all__ = ["SPEC", "MtkEmasBtcConfig", "CONFIG_DIR"]
