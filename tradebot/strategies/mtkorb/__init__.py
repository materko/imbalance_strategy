"""MTK ORB (MGC) — prieraz opening range 9:30–9:45 NY na zlate len v smere gapu a pri nie širokom range.

Logika je `orb15` s rozšíreniami `gapFilter` a `maxOrWidthMult` (rozbor NY open 11. 11. 2026: prieraz OR15 na MGC
v smere gapu, OR ≤ 1,25 × medián — 15 zo 16 rokov v zisku). Vlastný kľúč kvôli profilom, stránke a smernici, ktorá
ladí na všetkých dátach MGC (2010–2024) a odkladá 2 roky.
"""

from __future__ import annotations

from dataclasses import replace

from ..orb15 import SPEC as BASE_SPEC
from .config import CONFIG_DIR, MtkOrbConfig

SPEC = replace(
    BASE_SPEC,
    key="mtkorb",
    title="MTK ORB (MGC)",
    config_cls=MtkOrbConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_5m",
    logic_of="orb15",  # engine a čítanie polí má predloha
    freqtrade_class="MtkOrbStrategy",
    multicharts_class="MtkOrbSignal",
    multicharts_template="MtkOrb_Signal.py",
)

__all__ = ["SPEC", "MtkOrbConfig", "CONFIG_DIR"]
