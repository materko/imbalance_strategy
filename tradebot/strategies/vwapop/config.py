"""Config stratégie VWAP OP — prvý pullback k VWAP v smere driftu na vyššom TF.

Doslovný port Pine v6 skriptu "Drift VWAP Pullback Strategy" (IQCapital Clips, Matteo:
„This VWAP Strategy Has a 93.6% Chance of Getting You Funded"), 2026-09-29. Na rozdiel
od `vwapdrift` (ktorý je voľná rekonštrukcia rovnakej myšlienky s množstvom vlastných
prahov) je toto **presný port konkrétneho skriptu**: VWAP z 15m ukotvený na 9:30 New York,
drift meraný v jednotkách ATR **toho istého 15m TF** (nie ATR grafu), vstup market na
zavretí sviečky, ktorá sa dotkne VWAP a zavrie späť na strane driftu, SL pevne za VWAP,
TP z RR, voliteľný jednorazový posun SL na breakeven po +1R.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_filter import (ENTRY_FILTER_CONSTRAINTS, ENTRY_FILTER_ENUMS, ENTRY_FILTER_FIELD_NAMES,
                                        EntryFilterFields)
from tradebot.core.types import SizeSpec
from tradebot.core.entry_confirm import (ENTRY_CONFIRM_CONSTRAINTS, ENTRY_CONFIRM_ENUMS, ENTRY_CONFIRM_FIELD_NAMES,
                                         EntryConfirmFields)
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                          EntryOrderFields)

__all__ = ["VwapOpConfig", "CONFIG_DIR", "parse_session"]

#: Profily stratégie ležia pri nej, aby bol balík sebestačný.
CONFIG_DIR = Path(__file__).resolve().parent / "configs"


def parse_session(raw: str) -> tuple[int, int]:
    """Pine `input.session` tvaru `"HHMM-HHMM"` -> (začiatok, koniec) v minútach od polnoci.

    Seansa cez polnoc sa nepodporuje — tento skript ani jednu z troch (`rthSess`,
    `tradeWin`, `flatTime`) takú nemá.
    """
    parts = raw.split("-")
    if len(parts) != 2:
        raise ValueError(f"očakávaný tvar 'HHMM-HHMM', dostal {raw!r}")
    out = []
    for part in parts:
        part = part.strip()
        if len(part) != 4 or not part.isdigit():
            raise ValueError(f"'{part}' nie je HHMM")
        h, m = int(part[:2]), int(part[2:])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"'{part}' nie je platný čas")
        out.append(h * 60 + m)
    return out[0], out[1]


SIZE_FIELDS: ClassVar[dict[str, str]] = {
    "driftAtr": "atr",
    "tolAtr": "atr",
    "slAtr": "atr",
    "minSlDistance": "pct",
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "driftLen": (1, 20),
    "driftAtr": (0.0, 5.0),
    "tolAtr": (0.0, 2.0),
    "maxTrades": (1, 20),
    "slAtr": (0.0, 10.0),
    "rr": (0.1, 10.0),
    "riskDollar": (0, 100000),
    "minSlDistance": (0.0, 50.0),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"riskDollar", "legacyPineSizing", "minSlDistance", "leverage"})


@dataclass
class VwapOpConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Parametre VWAP OP. Defaulty = Pine skript (9:30 NY, VWAP z 15m, prvý pullback, RR 2)."""

    SIZE_FIELDS: ClassVar[dict[str, str]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES

    # ---- 📈 VWAP / Drift (HTF) --------------------------------------- #
    #: Timeframe VWAP a driftu (Pine `input.timeframe`) — musí byť násobkom TF grafu.
    htf: str = "15"
    #: RTH seansa (kotva VWAP aj hranica dňa), `America/New_York`.
    rthSess: str = "0930-1600"
    driftLen: int = 2
    driftAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.10, "atr"))
    needSide: bool = True
    # ---- 🚀 Vstupy (graf) --------------------------------------------- #
    tolAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.10, "atr"))
    needClose: bool = True
    firstOnly: bool = True
    maxTrades: int = 2
    tradeWin: str = "0945-1530"
    allowLong: bool = True
    allowShort: bool = True
    # ---- 🛡️ Risk / výstupy --------------------------------------------- #
    slAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.5, "atr"))
    rr: float = 2.0
    useBE: bool = False
    closeEOD: bool = False
    flatTime: str = "1555-1600"
    # ---- 🎨 Vzhľad ------------------------------------------------------- #
    showCross: bool = True
    colUp: str = "#22c55e"
    colDn: str = "#ef4444"
    colFlat: str = "#9ca3af"
    # ---- 🧩 Rozšírenia portu -------------------------------------------- #
    #: Pine má natvrdo 1 kontrakt (`default_qty_value = 1`) — riziko na obchod je rozšírenie portu.
    riskDollar: float = 100.0
    #: Doslovný Pine sizing (vždy 1 kontrakt), namiesto veľkosti z `riskDollar`.
    legacyPineSizing: bool = False
    #: Minimálna vzdialenosť SL od vstupu, inak sa obchod preskočí. 0 = vypnuté.
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    #: Páka vo Freqtrade futures.
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        """Veľkosť pozície — Pine má natvrdo 1 kontrakt, risk-based je rozšírenie portu."""
        if self.legacyPineSizing:
            return 1.0
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        for name in ("rthSess", "tradeWin", "flatTime"):
            raw = getattr(self, name)
            try:
                start, end = parse_session(raw)
            except ValueError as exc:
                yield f"{name}={raw!r}: {exc}"
                continue
            if end <= start:
                yield f"{name}={raw!r}: koniec musí byť za začiatkom (seansa cez polnoc sa nepodporuje)"
        try:
            htf_minutes = int(self.htf)
        except ValueError:
            yield f"htf={self.htf!r} nie je celé číslo minút"
        else:
            if htf_minutes < 1:
                yield f"htf={htf_minutes} musí byť >= 1"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
