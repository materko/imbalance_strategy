"""Config divergenčnej stratégie — port `DivergenceStrategy` (Freqtrade, 2022) do TradeBotu.

Stratégia nemá Pine predlohu; názvy polí sú preto voľné, ale kde sa dalo, kopírujú
pôvodné Freqtrade parametre (`prd`, `source`, `searchDiv`, `maxPp`, `maxBars`,
`dontConfirm`, `calc_<ind>_buy/sell` → `div<Ind>Long/Short`). Defaulty sú hodnoty
z posledného naladeného configu pôvodnej stratégie (`config_div_btc_15m.json`), nie
defaulty z tela triedy — tie mali všetky indikátory vypnuté a stratégia by neobchodovala.

Čo sa oproti originálu zmenilo a prečo: `docs/PORT.md` v tomto balíku.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeUnit, TradeDirection

__all__ = ["DivergenceConfig", "DivSource", "SearchDiv", "EntryMode", "CONFIG_DIR",
           "LONG_IND_FIELDS", "SHORT_IND_FIELDS"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class DivSource(str, Enum):
    """Z čoho sa berú pivoty a cena pre porovnanie (pôvodné `source`)."""

    CLOSE = "close"
    HIGH_LOW = "high/low"


class SearchDiv(str, Enum):
    """Ktoré divergencie sa hľadajú (pôvodné `search_div`)."""

    REGULAR = "regular"
    HIDDEN = "hidden"
    BOTH = "regular/hidden"


class EntryMode(str, Enum):
    """Ako sa zo signálu stane vstup."""

    #: pôvodný „trailing buy“: kým signál trvá, vstup až na bare, ktorý zavrie v smere obchodu
    #: nad/pod zatváracou cenou predchádzajúceho baru
    CONFIRM = "confirm"
    #: vstup na zatvorení signálneho baru
    IMMEDIATE = "immediate"


#: pole configu -> kľúč indikátora v detektore
LONG_IND_FIELDS: dict[str, str] = {
    "divMacdLong": "macd", "divMacdHistLong": "macdh", "divRsiLong": "rsi",
    "divStochLong": "stoch", "divCciLong": "cci", "divMomLong": "mom", "divObvLong": "obv",
    "divVwmacdLong": "vwmacd", "divCmfLong": "cmf", "divMfiLong": "mfi", "divCdvLong": "cdv",
}
SHORT_IND_FIELDS: dict[str, str] = {
    "divMacdShort": "macd", "divMacdHistShort": "macdh", "divRsiShort": "rsi",
    "divStochShort": "stoch", "divCciShort": "cci", "divMomShort": "mom", "divObvShort": "obv",
    "divVwmacdShort": "vwmacd", "divCmfShort": "cmf", "divMfiShort": "mfi", "divCdvShort": "cdv",
}

SIZE_FIELDS: dict[str, SizeUnit] = {}

ENUM_FIELDS: dict[str, type] = {
    "source": DivSource,
    "searchDiv": SearchDiv,
    "zoneSearchDiv": SearchDiv,
    "entryMode": EntryMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "prd": (1, 50),
    "maxPp": (1, 20),
    "maxBars": (30, 500),
    "minDivsLong": (1, 10),
    "minDivsShort": (1, 10),
    "signalBars": (1, 10),
    "stLen": (2, 100),
    "stMult": (0.5, 10),
    "stMultHtf": (0.5, 10),
    "htfMinutes": (5, 1440),
    "htf2Minutes": (5, 10080),
    "rsiLen": (2, 100),
    "rsiLongMax": (0, 100),
    "rsiShortMin": (0, 100),
    "zonePrd1": (1, 50),
    "zoneWindow1": (1, 200),
    "zonePrd2": (1, 50),
    "zoneWindow2": (1, 200),
    "zoneMaxPp": (1, 20),
    "zoneMaxBars": (30, 500),
    "atrLen": (2, 100),
    "slAtrMult": (0.2, 10),
    "rrRatio": (0, 20),
    "beActivationPct": (0, 50),
    "beLockPct": (0, 50),
    "trailActivationPct": (0, 50),
    "trailOffsetPct": (0.05, 50),
    "maxHoldBars": (0, 5000),
    "riskDollar": (0, 100000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class DivergenceConfig(StrategyConfig):
    """Defaulty = posledný naladený config pôvodnej stratégie (BTC 15m)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🔎 Divergencie --------------------------------------------------- #
    prd: int = 5
    source: DivSource = DivSource.CLOSE
    searchDiv: SearchDiv = SearchDiv.BOTH
    maxPp: int = 10
    maxBars: int = 200
    dontConfirm: bool = True
    minDivsLong: int = 1
    minDivsShort: int = 2
    signalBars: int = 3
    # ---- 📊 Indikátory long ----------------------------------------------- #
    divMacdLong: bool = True
    divMacdHistLong: bool = False
    divRsiLong: bool = True
    divStochLong: bool = True
    divCciLong: bool = False
    divMomLong: bool = True
    divObvLong: bool = True
    divVwmacdLong: bool = True
    divCmfLong: bool = True
    divMfiLong: bool = True
    divCdvLong: bool = True
    # ---- 📊 Indikátory short ---------------------------------------------- #
    divMacdShort: bool = True
    divMacdHistShort: bool = False
    divRsiShort: bool = True
    divStochShort: bool = False
    divCciShort: bool = False
    divMomShort: bool = False
    divObvShort: bool = False
    divVwmacdShort: bool = False
    divCmfShort: bool = False
    divMfiShort: bool = False
    divCdvShort: bool = False
    # ---- 📈 Trend --------------------------------------------------------- #
    stLen: int = 15
    stMult: float = 4.0
    htfMinutes: int = 60
    htf2Minutes: int = 240
    stMultHtf: float = 3.5
    pullbackFilter: bool = True
    rsiLen: int = 14
    rsiLongMax: float = 60.0
    rsiShortMin: float = 40.0
    # ---- 🧱 Divergenčné zóny HTF ------------------------------------------ #
    zoneFilter: bool = True
    zoneSearchDiv: SearchDiv = SearchDiv.REGULAR
    zonePrd1: int = 5
    zoneWindow1: int = 6
    zonePrd2: int = 3
    zoneWindow2: int = 44
    zoneMaxPp: int = 10
    zoneMaxBars: int = 200
    # ---- 🚪 Vstup --------------------------------------------------------- #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    entryMode: EntryMode = EntryMode.CONFIRM
    # ---- 🛑 Výstup -------------------------------------------------------- #
    atrLen: int = 14
    slAtrMult: float = 3.0
    rrRatio: float = 0.0
    trendExit: bool = True
    enableTrailing: bool = True
    beActivationPct: float = 1.5
    beLockPct: float = 0.35
    trailActivationPct: float = 4.0
    trailOffsetPct: float = 1.0
    maxHoldBars: int = 0
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 200.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showDivergences: bool = True
    showSupertrend: bool = True
    showZones: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    #: Páka vo Freqtrade futures (pôvodné `strat_lvrg`).
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    @property
    def long_indicators(self) -> frozenset[str]:
        return frozenset(k for f, k in LONG_IND_FIELDS.items() if getattr(self, f))

    @property
    def short_indicators(self) -> frozenset[str]:
        return frozenset(k for f, k in SHORT_IND_FIELDS.items() if getattr(self, f))

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.htf2Minutes < self.htfMinutes:
            yield (f"htf2Minutes={self.htf2Minutes} musí byť aspoň htfMinutes={self.htfMinutes}: "
                   "druhý vyšší TF je ten dlhší (pôvodne 4h nad 1h)")
        if self.tradeDirection is not TradeDirection.SHORT_ONLY and not self.long_indicators:
            yield "ani jeden indikátor pre long divergencie nie je zapnutý — long signál nemôže vzniknúť"
        if self.tradeDirection is not TradeDirection.LONG_ONLY and not self.short_indicators:
            yield "ani jeden indikátor pre short divergencie nie je zapnutý — short signál nemôže vzniknúť"
        if self.enableTrailing and self.beLockPct >= self.beActivationPct > 0:
            yield (f"beLockPct={self.beLockPct} musí byť menšie než beActivationPct={self.beActivationPct}: "
                   "zámok zisku nemôže ležať nad aktiváciou")
