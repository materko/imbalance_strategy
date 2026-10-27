"""`VwapOrbNetConfig` — tie isté parametre ako VWAP ORB (`tradebot/strategies/vwaporb/config.py`).

Parametre, rozsahy aj profily sú zámerne zhodné s predlohou, aby sa behy dali porovnať jedna k jednej;
číta ich C# jadro (`tradebot/csharp/TradeBot.Strategies/VwapOrbNet/VwapOrbConfig.cs`). Vlastná trieda je preto,
že registry hľadá stratégiu podľa triedy configu — a kvôli jednej kontrole navyše: stop posúvaný
s VWAP (`vwapStop`, `vwapTp`) C# port nemá (potrebuje stop meniaci sa v čase, ktorý nepoznajú ani živé
adaptéry), takže ho config odmietne skôr, než by beh ticho počítal niečo iné.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ..vwaporb.config import VwapOrbConfig

__all__ = ["VwapOrbNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class VwapOrbNetConfig(VwapOrbConfig):
    """Config VWAP ORB s jadrom v C# — polia, defaulty a kontroly dedí z VWAP ORB."""

    def _problems(self) -> Iterable[str]:
        yield from super()._problems()
        if self.vwapStop or self.vwapTp:
            yield ("vwapStop / vwapTp (stop posúvaný s VWAP) C# jadro nemá — nepoznajú ho ani NinjaTrader "
                   "a MT5; vypni ich, alebo použi stratégiu 'vwaporb'")
