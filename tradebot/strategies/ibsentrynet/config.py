"""`IBSEntryNetConfig` — tie isté parametre ako IBS Entry Zone (`tradebot/strategies/ibsentry/config.py`).

Prepis IBS Entry Zone s jadrom v C#; parametre, rozsahy aj profily sú zámerne zhodné, aby sa behy dali
porovnať jedna k jednej. Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy
configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibsentry.config import IBSEntryZoneConfig

__all__ = ["IBSEntryNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSEntryNetConfig(IBSEntryZoneConfig):
    """Config IBS Entry Zone s jadrom v C# — polia, defaulty a kontroly dedí z IBS Entry Zone; číta ich
    C# jadro (`tradebot/strategies/ibsentry/csharp/IbsEntryConfig.cs` nad `IbsNet/IbsConfig.cs`)."""
