"""Config stratégie Drift VWAP Pullback — prvý návrat k VWAP v smere jeho sklonu.

Stratégia nemá Pine predlohu (`pine_path=None`); vznikla z rozhovoru s Matteom (bývalý
market maker, Nordea Markets) na kanáli IQCapital, 2026: VWAP ukotvený na otvorení
9:30 New York, počítaný z 15m grafu a zobrazený na 5m grafe NQ; sklon VWAP („drift") určí
smer dňa a obchoduje sa **prvý pullback** ceny k VWAP v tom smere.

Video hovorí len toto. Všetko ďalšie — čo je „jasný drift", čo je „dotyk", kam ide stop,
aký je cieľ, dokedy sa vstupuje — tu je parameter s defaultom, ktorý je rozumný, nie
odvodený z videa. Prahy sú v ATR, nie v bodoch: rovnaký profil tak dáva zmysel na MNQ
aj na inom trhu so skutočným objemom.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["VwapDriftConfig", "VwapAnchor", "VwapPeriod", "EntryMode", "SlMode", "TradeDirection",
           "CONFIG_DIR"]

#: Profily stratégie ležia pri nej, aby bol balík sebestačný.
CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class VwapAnchor(str, Enum):
    """Odkiaľ sa VWAP počíta — kde sa každý deň vynuluje.

    * ``ny_open``  — od otvorenia cash seansy New York 9:30 (ako vo videu); do VWAP ide len RTH
    * ``session``  — klasický seansový VWAP CME futures: od 18:00 New York (Globex) do 17:00,
                     tak ho ukazuje TradingView s kotvou „Session" na NQ/MNQ
    * ``utc_day``  — kalendárny deň od 00:00 UTC; klasický VWAP na krypto burzách

    Obchodné okno (`sessionStart*` / `sessionEnd*`) sa kotvou nemení.
    """

    NY_OPEN = "ny_open"
    SESSION = "session"
    UTC_DAY = "utc_day"

    def window(self, start_minutes: int) -> tuple[int, int, str]:
        """(začiatok, koniec v minútach od polnoci, pásmo) pre `tradebot.core.vwap.SessionVwap`."""
        if self is VwapAnchor.SESSION:
            return 18 * 60, 17 * 60, "America/New_York"
        if self is VwapAnchor.UTC_DAY:
            return 0, 24 * 60, "UTC"
        return start_minutes, 16 * 60, "America/New_York"


class VwapPeriod(str, Enum):
    """Z akých sviečok sa VWAP počíta.

    * ``15``    — z 15-minútových sviečok zložených z barov grafu (ako vo videu); hodnota sa
                  mení pri zatvorení 15m sviečky a drift sa meria v 15m sviečkach
    * ``chart`` — priamo z barov grafu; hodnota sa mení na každom bare
    """

    M15 = "15"
    CHART = "chart"

    @property
    def minutes(self) -> int | None:
        return None if self is VwapPeriod.CHART else int(self.value)


class EntryMode(str, Enum):
    """Ako sa do pullbacku vstupuje. Signál (drift + odchod + návrat k VWAP) je ten istý.

    * ``close`` — market na zavretí baru, ktorý sa dotkol VWAP a zavrel späť na strane driftu
                  (odmietnutie VWAP je potvrdené, vstup je horší o kus od VWAP)
    * ``limit`` — limitka priamo na VWAP (± tolerancia dotyku) leží, kým cena nepríde;
                  najlepšia cena, ale vyplní sa aj pullback, ktorý VWAP prerazí
    * ``stop``  — po dotyku VWAP stop order nad high (short: pod low) pullbackového baru,
                  platí ``stopValidBars`` barov; vstúpi sa, až keď cena pokračuje v smere driftu

    Potvrdzovacie sviečky — po dotyku VWAP sa čaká najviac ``confirmBars`` barov (vrátane
    baru dotyku) a vstupuje sa market na zavretí prvej, ktorá sedí:

    * ``reaction``  — prvá reakčná sviečka do protipohybu: long prvá býčia (close > open),
                      short prvá medvedia
    * ``pinbar``    — pin bar: dlhý knôt smerom k VWAP (``pbWickPct`` % rozpätia), malé telo
                      (najviac ``pbBodyPct`` %)
    * ``engulfing`` — býčia (medvedia) sviečka, ktorej telo pohltí telo predošlej opačnej sviečky

    Keď cena medzitým zavrie za VWAP (o viac než toleranciu dotyku), pullback prerazil
    a čakanie sa zruší.
    """

    CLOSE = "close"
    LIMIT = "limit"
    STOP = "stop"
    REACTION = "reaction"
    PINBAR = "pinbar"
    ENGULFING = "engulfing"

    @property
    def confirms(self) -> bool:
        """Vstup čaká na potvrdzovaciu sviečku po dotyku."""
        return self in (EntryMode.REACTION, EntryMode.PINBAR, EntryMode.ENGULFING)


class SlMode(str, Enum):
    """Kam ide stop loss (každý + ``slBufferAtr`` × ATR, okrem ``atr``).

    * ``pullback`` — za extrém pullbacku (od dotyku po vstup), nikdy nie bližšie než VWAP
                     (pri ``limit`` vstupe extrém ešte nie je, ide za VWAP)
    * ``candle``   — pod low (short: nad high) vstupnej sviečky — pri ``reaction`` / ``pinbar``
                     / ``engulfing`` je to potvrdzovacia sviečka, pri ``close`` a ``stop``
                     pullbacková; pri ``limit`` ide za VWAP
    * ``vwap``     — za VWAP
    * ``atr``      — ``slAtr`` × ATR od vstupu
    * ``swing``    — za najnižší low (short: najvyšší high) posledných ``slSwingBars`` barov
    """

    PULLBACK = "pullback"
    CANDLE = "candle"
    VWAP = "vwap"
    ATR = "atr"
    SWING = "swing"


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "driftMinAtr": "atr",
    "awayAtr": "atr",
    "touchTolAtr": "atr",
    "slBufferAtr": "atr",
    "slAtr": "atr",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "vwapAnchor": VwapAnchor,
    "vwapPeriod": VwapPeriod,
    "tradeDirection": TradeDirection,
    "entryMode": EntryMode,
    "slMode": SlMode,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "sessionStartH": (0, 23),
    "sessionStartM": (0, 59),
    "sessionEndH": (0, 23),
    "sessionEndM": (0, 59),
    "driftBars": (1, 26),
    "driftMinAtr": (0.0, 5.0),
    "awayAtr": (0.0, 10.0),
    "touchTolAtr": (0.0, 2.0),
    "entryDelayMinutes": (0, 390),
    "entryWindowMinutes": (0, 390),
    "maxTradesPerDay": (1, 10),
    "atrLen": (2, 100),
    "stopValidBars": (1, 50),
    "confirmBars": (1, 50),
    "pbWickPct": (30, 95),
    "pbBodyPct": (5, 60),
    "slBufferAtr": (0.0, 5.0),
    "slAtr": (0.1, 10.0),
    "slSwingBars": (2, 100),
    "rrRatio": (0.25, 10.0),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"tickDollarValue", "legacyPineSizing", "minSlDistance", "leverage"})


@dataclass
class VwapDriftConfig(StrategyConfig):
    """Parametre Drift VWAP Pullback. Defaulty = video (9:30 NY, VWAP z 15m, prvý pullback)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🕐 Seansa -------------------------------------------------------- #
    #: Kotva VWAP a začiatok obchodovania v pásme America/New_York (9:30 = otvorenie cash
    #: seansy). Pásmo rieši letný čas samo.
    sessionStartH: int = 9
    sessionStartM: int = 30
    sessionEndH: int = 15
    sessionEndM: int = 55
    weekdaysOnly: bool = True
    # ---- 📈 VWAP a drift -------------------------------------------------- #
    vwapAnchor: VwapAnchor = VwapAnchor.NY_OPEN
    vwapPeriod: VwapPeriod = VwapPeriod.M15
    #: Drift = zmena VWAP za posledných `driftBars` periód VWAP (15m sviečok, resp. barov grafu).
    driftBars: int = 2
    driftMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    # ---- 🚀 Vstup (pullback) ---------------------------------------------- #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    entryMode: EntryMode = EntryMode.CLOSE
    stopValidBars: int = 3
    confirmBars: int = 3
    pbWickPct: int = 60
    pbBodyPct: int = 35
    #: Ako ďaleko od VWAP musí cena v smere driftu zavrieť, aby sa návrat počítal ako pullback.
    awayAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    #: Pullback = low (short: high) baru príde k VWAP bližšie než táto tolerancia.
    touchTolAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    firstPullbackOnly: bool = True
    entryDelayMinutes: int = 15
    entryWindowMinutes: int = 0
    maxTradesPerDay: int = 1
    # ---- 🛡️ Stop loss ----------------------------------------------------- #
    atrLen: int = 14
    slMode: SlMode = SlMode.PULLBACK
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.25, "atr"))
    slAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.5, "atr"))
    slSwingBars: int = 6
    # ---- 🎯 Cieľ ---------------------------------------------------------- #
    rrRatio: float = 2.0
    closeAtSessionEnd: bool = True
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showVwap: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    #: Hodnota jedného ticku v dolároch — CFD a futures ju potrebujú na risk-based sizing.
    tickDollarValue: float | None = None
    #: Doslovný Pine vzorec veľkosti pozície (`int()` + `max(1, …)`).
    legacyPineSizing: bool = False
    #: Minimálna vzdialenosť SL od vstupu, inak sa obchod preskočí. 0 = vypnuté.
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    #: Páka vo Freqtrade futures.
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def start_minutes(self) -> int:
        """Otvorenie seansy v minútach od polnoci New Yorku."""
        return self.sessionStartH * 60 + self.sessionStartM

    @property
    def end_minutes(self) -> int:
        return self.sessionEndH * 60 + self.sessionEndM

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        """Veľkosť pozície — jediné miesto, kde sa rozhoduje medzi Pine a opraveným vzorcom."""
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.end_minutes <= self.start_minutes + self.entryDelayMinutes:
            yield (f"koniec seansy {self.sessionEndH}:{self.sessionEndM:02d} je skôr než prvý "
                   f"povolený vstup — nezostal by ani jeden bar")
        if 0 < self.entryWindowMinutes <= self.entryDelayMinutes:
            yield (f"okno na vstup ({self.entryWindowMinutes} min) skončí skôr, než sa vstup "
                   f"vôbec povolí ({self.entryDelayMinutes} min po otvorení)")
