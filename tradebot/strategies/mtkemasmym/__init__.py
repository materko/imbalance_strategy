"""MTK EMAS 1.0 (MYM) — tá istá logika ako `mtkemas`, vlastné profily na MYM zo štúdie Mac mini (iCloud KLZAKY-STUDIA)."""

from __future__ import annotations

from dataclasses import replace

from ..mtkemas import SPEC as BASE_SPEC
from .config import CONFIG_DIR, MtkEmasMymConfig

SPEC = replace(
    BASE_SPEC,
    key="mtkemasmym",
    title="MTK EMAS 1.0 (MYM)",
    config_cls=MtkEmasMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_MYM",
    default_timeframe="2h",
    logic_of="mtkemas",  # engine a čítanie polí má predloha
    freqtrade_class="MtkEmasMymStrategy",
    multicharts_class="MtkEmasMymSignal",
    multicharts_template="MtkEmasMym_Signal.py",
)

__all__ = ["SPEC", "MtkEmasMymConfig", "CONFIG_DIR"]
