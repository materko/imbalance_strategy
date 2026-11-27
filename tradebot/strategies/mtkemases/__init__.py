"""MTK EMAS 1.0 (ES) — tá istá logika ako `mtkemas`, vlastné profily na ES zo štúdie Mac mini (iCloud KLZAKY-STUDIA)."""

from __future__ import annotations

from dataclasses import replace

from ..mtkemas import SPEC as BASE_SPEC
from .config import CONFIG_DIR, MtkEmasEsConfig

SPEC = replace(
    BASE_SPEC,
    key="mtkemases",
    title="MTK EMAS 1.0 (ES)",
    config_cls=MtkEmasEsConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_ES",
    default_timeframe="1h",
    logic_of="mtkemas",  # engine a čítanie polí má predloha
    freqtrade_class="MtkEmasEsStrategy",
    multicharts_class="MtkEmasEsSignal",
    multicharts_template="MtkEmasEs_Signal.py",
)

__all__ = ["SPEC", "MtkEmasEsConfig", "CONFIG_DIR"]
