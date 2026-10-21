"""Fibo 1.0 (MGC) — Fibo 1.0 na zlate (MGC futures): tá istá logika ako `fibo`, vlastné profily na MGC.

Variant existuje, aby boli nastavenia na zlato vo webapp v priečinku ZLATO oddelene od Nasdaqu; engine, parametre aj kresby
sú predlohy (`tradebot/strategies/fibo`). Profily sú najlepšie z víkendového hľadania na MGC (2.–5. 10. 2026) — v zisku všetkých
5 rokov 21/22 – 25/26 vrátane roka, ktorý hľadanie nevidelo, ale testované BEZ nákladov: WK 155 (RR 0,9; PF po rokoch 25/26 1,50 · 24/25 1,21 · 23/24 1,77 · 22/23 1,30 · 21/22 1,21) a WK 166 (RR 1,0; 1,55 · 1,30 · 1,46 · 1,21 · 1,09).
"""

from __future__ import annotations

from dataclasses import replace

from ..fibo import SPEC as BASE_SPEC
from .config import CONFIG_DIR, FiboMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="fibomgc",
    title="Fibo 1.0 (MGC)",
    config_cls=FiboMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="WK_fibo_MGC_155obch_WR63_R0_9",
    default_timeframe="3m",
    logic_of="fibo",  # engine a čítanie polí má predloha
    freqtrade_class="FiboMgcStrategy",
    multicharts_class="FiboMgcSignal",
    multicharts_template="FiboMgc_Signal.py",
)

__all__ = ["SPEC", "FiboMgcConfig", "CONFIG_DIR"]
