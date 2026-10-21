"""Scalping 3MA (MGC) — Scalping 3MA na zlate (MGC futures): tá istá logika ako `scalp3ma`, vlastné profily na MGC.

Variant existuje, aby boli nastavenia na zlato vo webapp v priečinku ZLATO oddelene od Nasdaqu; engine, parametre aj kresby
sú predlohy (`tradebot/strategies/scalp3ma`). Profily sú najlepšie z víkendového hľadania na MGC (2.–5. 10. 2026) — v zisku všetkých
5 rokov 21/22 – 25/26 vrátane roka, ktorý hľadanie nevidelo, ale testované BEZ nákladov: WK 159 (RR 0,9; PF 1,23 · 1,32 · 1,33 · 1,32 · 1,30), WK 161 (RR 1,2; 1,44 · 1,39 · 1,34 · 1,21 · 1,26), WK 156 (3m, RR 2,0; 1,33 · 1,42 · 1,21 · 1,28 · 1,14) a WK 169 (RR 1,4; 1,33 · 1,32 · 1,27 · 1,21 · 1,03).
"""

from __future__ import annotations

from dataclasses import replace

from ..scalp3ma import SPEC as BASE_SPEC
from .config import CONFIG_DIR, Scalp3MaMgcConfig

SPEC = replace(
    BASE_SPEC,
    key="scalp3mamgc",
    title="Scalping 3MA (MGC)",
    config_cls=Scalp3MaMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="WK_scalp3ma_MGC_159obch_WR57_R0_9",
    default_timeframe="15m",
    logic_of="scalp3ma",  # engine a čítanie polí má predloha
    freqtrade_class="Scalp3MaMgcStrategy",
    multicharts_class="Scalp3MaMgcSignal",
    multicharts_template="Scalp3MaMgc_Signal.py",
)

__all__ = ["SPEC", "Scalp3MaMgcConfig", "CONFIG_DIR"]
