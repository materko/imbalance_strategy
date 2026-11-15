"""`IBSEntryEurConfig` — tie isté parametre ako `ibsentrymym` (`tradebot/strategies/ibsentrymym/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibsentrymym.config import IBSEntryMymConfig

__all__ = ["IBSEntryEurConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSEntryEurConfig(IBSEntryMymConfig):
    """Config IBS EZ 6E — polia, defaulty a kontroly dedí z predlohy."""
