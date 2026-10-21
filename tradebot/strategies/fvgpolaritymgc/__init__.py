"""FVG POLARITY (MGC) — FVG POLARITY na zlate (MGC futures): tá istá logika ako `fvgpolarity`, vlastné profily na MGC.

Variant existuje, aby boli nastavenia na zlato vo webapp v priečinku ZLATO oddelene od Nasdaqu; engine, parametre aj kresby
sú predlohy (`tradebot/strategies/fvgpolarity`). Profily: 2 najlepšie z víkendového hľadania na MGC (5. 10. 2026; WK 161 a WK 221 — v zisku aj na starších rokoch),
testované bez nákladov (SL 2 body) — pred použitím ich treba preveriť podľa smernice.
"""

from __future__ import annotations

from dataclasses import replace

from ..fvgpolarity import SPEC as BASE_SPEC
from .config import CONFIG_DIR, FvgPolarityMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="fvgpolaritymgc",
    title="FVG POLARITY (MGC)",
    config_cls=FvgPolarityMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="WK_fvgpolarity_MGC_161obch_WR61_R1_1",
    default_timeframe="3m",
    logic_of="fvgpolarity",  # engine a čítanie polí má predloha
    freqtrade_class="FvgPolarityMgcStrategy",
    multicharts_class="FvgPolarityMgcSignal",
    multicharts_template="FvgPolarityMgc_Signal.py",
)

__all__ = ["SPEC", "FvgPolarityMgcConfig", "CONFIG_DIR"]
