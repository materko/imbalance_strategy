"""Platformovo neutrálne príkazy na kreslenie + paleta.

Engine **nikdy nekreslí sám** — vracia zoznam `DrawCommand`. Každý adaptér má
`DrawSink`, ktorý ich premení na natívne objekty (MultiCharts `DrwRectangle`,
plotly shapes vo Freqtrade). To je jediný spôsob, ako dostať naozaj rovnaké
vykreslenie na oboch platformách aj v TradingView.

### Prečo majú objekty identitu
Pine kreslí objekt raz (`box.new`) a potom ho **mení** — 16× `box.set_right`,
`box.set_bgcolor`, `box.set_border_color`. Zóna sa počas života predlžuje doprava
a pri prechode stavom mení farbu. Snapshot z okamihu vzniku by teda nakreslil
niečo iné než to, čo je na grafe nakoniec vidieť.

Preto má každý objekt `obj_id` a engine emituje aj `DrawUpdate` — presný náprotivok
Pine `set_*`. `DrawRegistry` to prehrá a vráti finálny stav; adaptér, ktorý chce
animáciu alebo replay, si namiesto toho môže prehrať príkazy po baroch.

Paleta je prevzatá 1:1 z Pine sekcie „DESIGN SYSTEM" (riadky 258–266).
LONG/Demand je zámerne červená a SHORT/Supply modrá — je to konvencia tejto
stratégie, nie preklep.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "Palette",
    "PAL",
    "LineStyle",
    "LabelStyle",
    "DrawKind",
    "DrawBox",
    "DrawLine",
    "DrawLabel",
    "DrawBg",
    "DrawUpdate",
    "DrawDelete",
    "DrawCommand",
    "DrawObject",
    "DrawRegistry",
    "zone_color",
    "with_alpha",
    "object_to_dict",
    "objects_to_dicts",
    "merge_backgrounds",
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


class LabelStyle(str, Enum):
    """Pine `label.style_*` — určuje, či má štítok bublinu a kam smeruje."""

    NONE = "none"  # label.style_none - holý text
    UP = "up"  # label.style_label_up - bublina pod bodom, šípka hore
    DOWN = "down"  # label.style_label_down
    LEFT = "left"  # label.style_label_left


class DrawKind(str, Enum):
    """Čo objekt znamená — adaptér podľa toho volí vrstvu a štýl.

    Hodnoty kopírujú miesta v Pine, aby sa dali porovnať vedľa seba.
    """

    # -- SD zóny a ich sprievodné boxy (Pine 652, 656, 697, 1684, 1758) ----
    SD_ZONE_PRE = "sd_zone_pre"  # formácia zóny, bodkovaný obrys bez výplne
    SD_ZONE_POST = "sd_zone_post"  # potvrdená zóna, plná výplň
    IMB_BOX = "imb_box"
    PIN_BAR_BOX = "pin_bar_box"  # Pine 1572
    ENGULFING_BOX = "engulfing_box"  # Pine 1617
    # -- obchod (Pine 2097, 2098) -----------------------------------------
    TP_BOX = "tp_box"
    SL_BOX = "sl_box"
    ENTRY = "entry"
    EXIT = "exit"
    # -- štítky stavového automatu ----------------------------------------
    SKIP = "skip"  # Pine 2042
    COUNTER = "counter"  # Pine 2265
    STATE34 = "state34"  # Pine 1850 / 1872
    EXPIRED = "expired"  # Pine 2173
    MAX_DAILY = "max_daily"  # Pine 1894
    IMB_ZERO = "imb_zero"  # Pine 2246 - "0" pri imbalance
    # -- display-only moduly ----------------------------------------------
    SWING = "swing"  # HH/HL/LH/LL štítky (Pine 750, 762)
    STRUCTURE = "structure"  # BOS/CHoCH čiara + štítok (Pine 781-812)
    SR_LEVEL = "sr_level"  # Pine 1126 / 1129
    SR_GOLDEN = "sr_golden"  # Pine 1114 / 1117
    LIQ_SWEEP = "liq_sweep"  # Pine 1181-1231
    ELLIOTT_WAVE = "elliott_wave"  # Pine 1346 / 1357
    ELLIOTT_PROJ = "elliott_proj"  # Pine 1425 / 1468
    # -- pozadie seansy (Pine 331-333) ------------------------------------
    SESSION = "session"


@dataclass(slots=True)
class DrawBox:
    """Obdĺžnik. Súradnice X sú **čas v ms**, nie index baru — aby boli prenositeľné.

    Nie je frozen: Pine ten istý box počas života mení (`box.set_right` na každom
    bare, `set_bgcolor` pri zmene stavu) a `DrawRegistry` to reprodukuje.
    """

    kind: DrawKind
    x1_ms: int
    y1: float
    x2_ms: int
    y2: float
    border_color: str
    fill_color: str | None = None
    border_style: LineStyle = LineStyle.SOLID
    border_width: int = 1
    #: Pine `extend.right` — box pokračuje za pravý okraj.
    extend_right: bool = False
    obj_id: str = ""
    zone_uid: int | None = None
    text: str = ""

    def __post_init__(self) -> None:
        if self.x2_ms < self.x1_ms:
            raise ValueError(f"box konci pred zaciatkom: {self.x1_ms} -> {self.x2_ms}")


@dataclass(slots=True)
class DrawLine:
    kind: DrawKind
    x1_ms: int
    y1: float
    x2_ms: int
    y2: float
    color: str
    style: LineStyle = LineStyle.SOLID
    width: int = 1
    obj_id: str = ""
    zone_uid: int | None = None
    text: str = ""


@dataclass(slots=True)
class DrawLabel:
    kind: DrawKind
    x_ms: int
    y: float
    text: str
    color: str
    #: Pine `label.style_*`. `above` sa zachováva pre spätnú kompatibilitu.
    style: LabelStyle = LabelStyle.NONE
    above: bool = True
    #: Farba bubliny; `None` = priehľadná (Pine `color.new(color.white, 100)`).
    bg_color: str | None = None
    obj_id: str = ""
    zone_uid: int | None = None


@dataclass(slots=True)
class DrawBg:
    """Pine `bgcolor()` — zvislý pás cez celú výšku grafu (pozadie seansy)."""

    kind: DrawKind
    x1_ms: int
    x2_ms: int
    color: str
    obj_id: str = ""
    text: str = ""


@dataclass(frozen=True, slots=True)
class DrawUpdate:
    """Pine `box.set_*` / `label.set_*` — zmena už nakresleného objektu.

    `field` je názov atribútu cieľového objektu (napr. ``"x2_ms"``, ``"fill_color"``).
    """

    obj_id: str
    field: str
    value: object


@dataclass(frozen=True, slots=True)
class DrawDelete:
    """Pine `box.delete` / `label.delete` — objekt vypadol z poolu."""

    obj_id: str


DrawObject = DrawBox | DrawLine | DrawLabel | DrawBg
DrawCommand = DrawObject | DrawUpdate | DrawDelete


class DrawRegistry:
    """Prehrá príkazy a vráti finálny stav objektov — to, čo je na grafe vidieť.

    Adaptér, ktorý chce statický obrázok, prehrá celý beh a vykreslí `objects()`.
    Adaptér, ktorý chce replay, si príkazy vezme po baroch a registry nepoužije.
    """

    __slots__ = ("_objects",)

    def __init__(self) -> None:
        self._objects: dict[str, DrawObject] = {}

    def apply(self, cmd: DrawCommand) -> None:
        if isinstance(cmd, DrawUpdate):
            obj = self._objects.get(cmd.obj_id)
            if obj is not None:  # update na zmazaný objekt sa ticho ignoruje
                setattr(obj, cmd.field, cmd.value)
            return
        if isinstance(cmd, DrawDelete):
            self._objects.pop(cmd.obj_id, None)
            return
        if not cmd.obj_id:
            raise ValueError(f"objekt bez obj_id sa nedá updatovať: {cmd}")
        self._objects[cmd.obj_id] = cmd

    def extend(self, cmds: "Iterable[DrawCommand]") -> None:
        for c in cmds:
            self.apply(c)

    def objects(self, kind: DrawKind | None = None) -> list[DrawObject]:
        """Finálny stav, v poradí vzniku (Pine kreslí neskoršie objekty navrch)."""
        out = list(self._objects.values())
        return [o for o in out if o.kind is kind] if kind is not None else out

    def __len__(self) -> int:
        return len(self._objects)


# --------------------------------------------------------------------------- #
# Serializácia — finálny stav objektov ako kompaktný JSON
#
# Webapp si kresby behu odkladá k výsledku (`chart.json.gz`), aby sa graf dal
# pozrieť aj po týždňoch bez toho, aby sa engine musel prehrať znova (ročný beh
# je desiatky sekúnd). Kľúče sú krátke zámerne: ročný beh má desaťtisíce objektov.
# --------------------------------------------------------------------------- #


def merge_backgrounds(objects: "Iterable[DrawObject]") -> list[DrawObject]:
    """Zlúči susedné pásy pozadia rovnakej farby do jedného — Pine `bgcolor()` je
    jeden pás na bar, takže ročný beh by inak mal ~60 000 pásov seansy.

    Ostatné objekty prechádzajú nezmenené a v pôvodnom poradí; zlúčené pásy sú
    na mieste svojho prvého člena.
    """
    out: list[DrawObject] = []
    open_bands: dict[tuple[str, str], DrawBg] = {}
    for o in objects:
        if not isinstance(o, DrawBg):
            out.append(o)
            continue
        key = (o.color, o.text)
        prev = open_bands.get(key)
        if prev is not None and o.x1_ms <= prev.x2_ms and o.x2_ms >= prev.x1_ms:
            prev.x2_ms = max(prev.x2_ms, o.x2_ms)
            prev.x1_ms = min(prev.x1_ms, o.x1_ms)
            continue
        band = DrawBg(kind=o.kind, x1_ms=o.x1_ms, x2_ms=o.x2_ms, color=o.color, obj_id=o.obj_id, text=o.text)
        open_bands[key] = band
        out.append(band)
    return out


def object_to_dict(o: DrawObject) -> dict:
    """Jeden objekt → slovník s krátkymi kľúčmi (`t` typ, `k` druh).

    Prázdne a predvolené polia sa vynechávajú, aby bol súbor malý; `obj_id` sa
    neukladá vôbec — po prehratí `DrawRegistry` už identitu nikto nepotrebuje
    a na ročnom behu robí pätinu súboru.
    """
    d: dict = {"k": o.kind.value}
    if isinstance(o, DrawBox):
        d.update(t="box", x1=o.x1_ms, y1=o.y1, x2=o.x2_ms, y2=o.y2, bc=o.border_color)
        if o.fill_color:
            d["fc"] = o.fill_color
        if o.border_style is not LineStyle.SOLID:
            d["bs"] = o.border_style.value
        if o.border_width != 1:
            d["bw"] = o.border_width
        if o.extend_right:
            d["er"] = True
    elif isinstance(o, DrawLine):
        d.update(t="line", x1=o.x1_ms, y1=o.y1, x2=o.x2_ms, y2=o.y2, c=o.color)
        if o.style is not LineStyle.SOLID:
            d["s"] = o.style.value
        if o.width != 1:
            d["w"] = o.width
    elif isinstance(o, DrawLabel):
        d.update(t="label", x=o.x_ms, y=o.y, tx=o.text, c=o.color, ab=o.above)
        if o.style is not LabelStyle.NONE:
            d["s"] = o.style.value
        if o.bg_color:
            d["bg"] = o.bg_color
    elif isinstance(o, DrawBg):
        d.update(t="bg", x1=o.x1_ms, x2=o.x2_ms, c=o.color)
    else:  # pragma: no cover - nový typ objektu treba doplniť aj sem
        raise TypeError(f"neznámy objekt na serializáciu: {type(o).__name__}")
    text = getattr(o, "text", "")
    if text and "tx" not in d:
        d["tx"] = text
    zone_uid = getattr(o, "zone_uid", None)
    if zone_uid is not None:
        d["z"] = zone_uid
    return d


def objects_to_dicts(objects: "Iterable[DrawObject]") -> list[dict]:
    """Zoznam objektov → JSON-serializovateľný zoznam, s pásmi pozadia zlúčenými."""
    return [object_to_dict(o) for o in merge_backgrounds(objects)]
