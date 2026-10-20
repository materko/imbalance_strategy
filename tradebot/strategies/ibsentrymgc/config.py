"""`IBSEntryMgcConfig` — tie isté parametre ako IBS Entry Zone (`tradebot/strategies/ibsentry/config.py`).

IBS EZ MGC je IBS Entry Zone pre zlato (MGC, Micro Gold futures). Logika ani parametre sa nemenia; rozdiel je
v profiloch: prahy, ktoré sú v IBS v bodoch alebo tickoch (imbalance, pin bar, engulfing, zhluk S/R, FVG,
vzdialenosti v tickoch), sú v profiloch tejto stratégie v **násobkoch ATR** (`{"value": …, "unit": "atr"}`),
lebo zlato stálo 2021 okolo 1 800 $ a 2026 okolo 4 000 $ — pevný bod by znamenal každý rok inú stratégiu.
Vlastná trieda existuje preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`), a aby
stratégie na NQ (`ibsentry`, `ibsentrynet`) ostali bez zásahu.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibsentry.config import IBSEntryZoneConfig

__all__ = ["IBSEntryMgcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSEntryMgcConfig(IBSEntryZoneConfig):
    """Config IBS EZ MGC — polia, defaulty a kontroly dedí z IBS Entry Zone."""
