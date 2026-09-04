"""Platformovo neutrálne príkazy na kreslenie + paleta.

Engine **nikdy nekreslí sám** — vracia zoznam `DrawCommand`. Každý adaptér má
`DrawSink`, ktorý ich premení na natívne objekty (MultiCharts `DrwRectangle`,
plotly shapes vo Freqtrade). To je jediný spôsob, ako dostať naozaj rovnaké
vykreslenie na oboch platformách aj v TradingView.

Paleta je prevzatá 1:1 z Pine sekcie „DESIGN SYSTEM" (riadky 258–266).
LONG/Demand je zámerne červená a SHORT/Supply modrá — je to konvencia tejto
stratégie, nie preklep.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "Palette",
    "PAL",
    "LineStyle",
    "DrawKind",
    "DrawBox",
    "DrawLine",
    "DrawLabel",
    "DrawCommand",
    "zone_color",
    "with_alpha",
]


class Palette(str, Enum):
    """Farby ako hex. Hodnoty zodpovedajú `color.rgb(...)` v Pine."""

    LONG = "#be3c46"  # rgb(190, 60, 70)   tlmená tehlová - LONG/Demand
    SHORT = "#3b82f6"  # rgb(59, 130, 246)  modrá - SHORT/Supply
    STRONG = "#10b981"  # rgb(16, 185, 129)  smaragd - volume-potvrdené zóny
    AMBER = "#d97706"  # rgb(217, 119, 6)   CHoCH, expirované, riziko
    SLATE = "#334155"  # rgb(51, 65, 85)    štruktúra čiar/textu
    GRAY = "#94a3b8"  # rgb(148, 163, 184) skip/neaktívne
    SESSION1 = "#6366f1"  # rgb(99, 102, 241)  indigo
    SESSION2 = "#0d9488"  # rgb(13, 148, 136)  tyrkysová
    SESSION3 = "#9333ea"  # rgb(147, 51, 234)  fialová


#: Alias, aby sa dalo písať `PAL.LONG`.
PAL = Palette


def with_alpha(color: str, transparency: int) -> str:
    """Pine `color.new(c, transparency)` → hex s alfa kanálom.

    Pine udáva **priehľadnosť** 0–100 (0 = nepriehľadné), CSS/hex udáva **krytie**.
    """
    if not 0 <= transparency <= 100:
        raise ValueError(f"transparency musí byť 0-100, je {transparency}")
    alpha = round((100 - transparency) / 100 * 255)
    return f"{color}{alpha:02x}"


def zone_color(direction: int, strong: bool) -> str:
    """Pine `f_zoneColor` (riadok 594)."""
    if strong:
        return Palette.STRONG.value
    return Palette.LONG.value if direction == 1 else Palette.SHORT.value


class LineStyle(str, Enum):
    SOLID = "solid"
    DOTTED = "dotted"
    DASHED = "dashed"


class DrawKind(str, Enum):
    """Čo objekt znamená — adaptér podľa toho volí vrstvu a štýl."""

    SD_ZONE_PRE = "sd_zone_pre"  # formácia zóny, bodkovaný obrys bez výplne
    SD_ZONE_POST = "sd_zone_post"  # potvrdená zóna, plná výplň
    IMB_BOX = "imb_box"
    TP_BOX = "tp_box"
    SL_BOX = "sl_box"
    STRUCTURE = "structure"
    SR_LEVEL = "sr_level"
    LIQ_SWEEP = "liq_sweep"
    SKIP = "skip"
    COUNTER = "counter"
    ENTRY = "entry"
    EXIT = "exit"


@dataclass(frozen=True, slots=True)
class DrawBox:
    """Obdĺžnik. Súradnice X sú **čas v ms**, nie index baru — aby boli prenositeľné."""

    kind: DrawKind
    x1_ms: int
    y1: float
    x2_ms: int
    y2: float
    border_color: str
    fill_color: str | None = None
    border_style: LineStyle = LineStyle.SOLID
    zone_uid: int | None = None
    text: str = ""

    def __post_init__(self) -> None:
        if self.x2_ms < self.x1_ms:
            raise ValueError(f"box konci pred zaciatkom: {self.x1_ms} -> {self.x2_ms}")


@dataclass(frozen=True, slots=True)
class DrawLine:
    kind: DrawKind
    x1_ms: int
    y1: float
    x2_ms: int
    y2: float
    color: str
    style: LineStyle = LineStyle.SOLID
    width: int = 1
    text: str = ""


@dataclass(frozen=True, slots=True)
class DrawLabel:
    kind: DrawKind
    x_ms: int
    y: float
    text: str
    color: str
    above: bool = True
    zone_uid: int | None = None


DrawCommand = DrawBox | DrawLine | DrawLabel
