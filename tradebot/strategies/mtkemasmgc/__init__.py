"""MTK EMAS 1.0 (MGC) — tá istá logika ako `mtkemas`, vlastné profily na MGC zo štúdie Mac mini (iCloud KLZAKY-STUDIA)."""

from __future__ import annotations

from dataclasses import replace

from ..mtkemas import SPEC as BASE_SPEC
from .config import CONFIG_DIR, MtkEmasMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="mtkemasmgc",
    title="MTK EMAS 1.0 (MGC)",
    config_cls=MtkEmasMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_MGC",
    default_timeframe="4h",
    logic_of="mtkemas",  # engine a čítanie polí má predloha
    freqtrade_class="MtkEmasMgcStrategy",
    multicharts_class="MtkEmasMgcSignal",
    multicharts_template="MtkEmasMgc_Signal.py",
)

__all__ = ["SPEC", "MtkEmasMgcConfig", "CONFIG_DIR"]
