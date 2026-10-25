"""`IBSEntryEsNetConfig` — parametre IBS Entry Zone (C# jadro) a navyše filter trendu / volatility (ako `ibsentryes`).

Vlastná trieda: registry hľadá stratégiu podľa triedy configu (`spec_for_config`) a IBS rodina na NQ filter nemá.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from tradebot.core.entry_filter import (ENTRY_FILTER_CONSTRAINTS, ENTRY_FILTER_ENUMS, ENTRY_FILTER_FIELD_NAMES,
                                        EntryFilterFields)

from ..ibsentrynet.config import IBSEntryNetConfig

__all__ = ["IBSEntryEsNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSEntryEsNetConfig(IBSEntryNetConfig, EntryFilterFields):
    """Config IBS EZ ES (C# jadro) — polia IBS Entry Zone + spoločný filter trendu a volatility (predvolene vypnutý)."""

    ENUM_FIELDS: ClassVar[dict[str, type]] = {**IBSEntryNetConfig.ENUM_FIELDS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**IBSEntryNetConfig.CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = IBSEntryNetConfig.PORT_ONLY_FIELDS | ENTRY_FILTER_FIELD_NAMES
