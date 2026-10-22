"""`IBSEntryEsConfig` — tie isté parametre ako IBS Entry Zone (`tradebot/strategies/ibsentry/config.py`).

IBS EZ ES je IBS Entry Zone pre S&P 500 futures (ES). Logika ani parametre sa nemenia; rozdiel je
v profiloch: prahy, ktoré sú v IBS v bodoch alebo tickoch (imbalance, pin bar, engulfing, zhluk S/R, FVG,
vzdialenosti v tickoch), sú v profiloch tejto stratégie v **násobkoch ATR** (`{"value": …, "unit": "atr"}`),
lebo ES sa hýbe asi 4,5× menej bodov ako NQ (medián ATR 3m 2,16 vs 9,74) — prahy z NQ v bodoch by na ES nesedeli.
Vlastná trieda existuje preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`), a aby
stratégie na NQ (`ibsentry`, `ibsentrynet`) ostali bez zásahu.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from tradebot.core.entry_filter import (ENTRY_FILTER_CONSTRAINTS, ENTRY_FILTER_ENUMS, ENTRY_FILTER_FIELD_NAMES,
                                        EntryFilterFields)

from ..ibsentry.config import CONSTRAINTS as BASE_CONSTRAINTS
from ..ibsentry.config import ENUM_FIELDS as BASE_ENUM_FIELDS
from ..ibsentry.config import IBSEntryZoneConfig

__all__ = ["IBSEntryEsConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSEntryEsConfig(IBSEntryZoneConfig, EntryFilterFields):
    """Config IBS EZ ES — polia, defaulty a kontroly dedí z IBS Entry Zone; navyše spoločný filter trendu
    a volatility (`tradebot/core/entry_filter.py`, predvolene vypnutý), ktorý IBS rodina na NQ nemá.
    Prevzatý z IBS EZ MGC (22. 10. 2026)."""

    ENUM_FIELDS: ClassVar[dict[str, type]] = {**BASE_ENUM_FIELDS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**BASE_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = IBSEntryZoneConfig.PORT_ONLY_FIELDS | ENTRY_FILTER_FIELD_NAMES
