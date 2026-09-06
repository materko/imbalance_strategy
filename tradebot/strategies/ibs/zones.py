"""Detekcia SD zón na detekčnom TF + evidencia zón.

Replika Pine riadkov 274–279 (`snapTime`), 357–392 (pattern) a 638–660
(vytvorenie zóny a jej dvoch boxov).

Pattern sa hľadá na **štyroch uzavretých baroch detekčného TF**. Pine ich ťahá
jedným `request.security` s offsetom ``[1]``..``[4]``; tu prichádzajú ako
`HTFWindow.bars[0..3]`, kde `bars[0]` je posledný uzavretý bar.

Zóna sama je vždy rozsah **najstaršieho** z tých štyroch barov (`bars[3]`) —
tej sviečky, ktorá impulz odštartovala.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .config import IBSConfig
from tradebot.core.drawing import DrawBox, DrawKind, DrawUpdate, LineStyle, with_alpha, zone_color
from tradebot.core.types import Direction, HTFWindow, InstrumentSpec, SnapMode

__all__ = [
    "ZoneSource",
    "Zone",
    "SdPattern",
    "snap_time",
    "detect_sd_pattern",
    "ZoneBook",
    "MAX_ZONES_HARD_CAP",
]

#: Pine `maxSdZonesEff = math.min(maxSdZones, 200)` — strop nad rámec configu.
MAX_ZONES_HARD_CAP = 200


class ZoneSource(int, Enum):
    """Pine `srcIn` v `f_pushZone`."""

    SD = 0
    SR = 1
    LIQUIDITY = 2


def snap_time(t_ms: int, step_ms: int, mode: SnapMode) -> int:
    """Pine `snapTime` (riadok 276) — zarovnanie na grid aktuálneho TF grafu.

    Musí sedieť na milisekundu, inak sa zóny nakreslia inde než v TradingView.
    Pine počíta ``math.floor(t / stepMs) * stepMs`` v plávajúcej desatinnej čiarke
    a až výsledok pretypuje na int; pri týchto veľkostiach je to zhodné
    s celočíselnou aritmetikou, ktorú používame tu.
    """
    if mode is SnapMode.OFF or step_ms <= 0:
        return t_ms
    if mode is SnapMode.FLOOR:
        return math.floor(t_ms / step_ms) * step_ms
    if mode is SnapMode.CEIL:
        return math.ceil(t_ms / step_ms) * step_ms
    return round(t_ms / step_ms) * step_ms


@dataclass(frozen=True, slots=True)
class SdPattern:
    """Výsledok hľadania patternu na detekčnom TF."""

    direction: Direction
    top: float
    bot: float
    base_ms: int  # Pine zT05 - čas najstaršieho baru (bars[3])
    confirm_ms: int  # Pine zTConf5 - čas posledného uzavretého baru (bars[0])
    volume_strong: bool
    variant: str  # ktorá z troch vetiev pattern spustila - na ladenie


def _is_bull(b) -> bool:
    return b.close > b.open


def _is_bear(b) -> bool:
    return b.close < b.open


def detect_sd_pattern(
    htf: HTFWindow,
    cfg: IBSConfig,
    inst: InstrumentSpec,
    *,
    atr: float = 0.0,
) -> SdPattern | None:
    """Pine riadky 357–392. Vráti pattern, alebo `None` ak žiadny nesedí.

    Tri varianty pre každý smer (na príklade LONG):
      * ``V1`` — bear, bull, bull, bull: tri rastúce sviečky po klesajúcej
      * ``V2`` — bear, bull + imbalance medzi `bars[0].low` a `bars[2].high`
      * ``V3`` — bear, bull + imbalance medzi `bars[1].low` a `bars[3].high`

    Volume filter blokuje vznik zóny len ak sú zapnuté OBE prepínače
    (`useVolumeFilter` aj `volumeFilterBlockTrading`) — inak sa zóna vytvorí
    a `volume_strong` slúži už len na farbenie.
    """
    b0, b1, b2, b3 = htf.bars

    min_imb = cfg.minImbSizePoints.resolve(inst, price=b0.close, atr=atr)

    bull_imb_1 = (b0.low - b2.high) >= min_imb and b0.low > b2.high
    bear_imb_1 = (b2.low - b0.high) >= min_imb and b0.high < b2.low
    bull_imb_2 = (b1.low - b3.high) >= min_imb and b1.low > b3.high
    bear_imb_2 = (b3.low - b1.high) >= min_imb and b1.high < b3.low

    long_v1 = _is_bear(b3) and _is_bull(b2) and _is_bull(b1) and _is_bull(b0)
    long_v2 = _is_bear(b3) and _is_bull(b2) and bull_imb_1
    long_v3 = _is_bear(b3) and _is_bull(b2) and bull_imb_2
    short_v1 = _is_bull(b3) and _is_bear(b2) and _is_bear(b1) and _is_bear(b0)
    short_v2 = _is_bull(b3) and _is_bear(b2) and bear_imb_1
    short_v3 = _is_bull(b3) and _is_bear(b2) and bear_imb_2

    if long_v1 or long_v2 or long_v3:
        direction = Direction.LONG
        variant = "V1" if long_v1 else ("V2" if long_v2 else "V3")
    elif short_v1 or short_v2 or short_v3:
        direction = Direction.SHORT
        variant = "V1" if short_v1 else ("V2" if short_v2 else "V3")
    else:
        return None

    # Pine zVolStrongCalc - priemer volume troch impulznych sviecok vs SMA.
    avg_impulse_vol = (b0.volume + b1.volume + b2.volume) / 3.0
    volume_strong = (
        cfg.useVolumeFilter and htf.vol_sma > 0 and avg_impulse_vol >= cfg.volMultiplier * htf.vol_sma
    )
    if cfg.useVolumeFilter and cfg.volumeFilterBlockTrading and not volume_strong:
        return None

    return SdPattern(
        direction=direction,
        top=b3.high,
        bot=b3.low,
        base_ms=b3.time,
        confirm_ms=b0.time,
        volume_strong=volume_strong,
        variant=f"{'long' if direction is Direction.LONG else 'short'}{variant}",
    )


@dataclass
class Zone:
    """Jedna zóna v evidencii vrátane stavu jej životného cyklu (STATE 0-5)."""

    uid: int
    direction: Direction
    top: float
    bot: float
    created_ms: int  # Pine leftT - snapnutý čas základovej sviečky
    confirmed_ms: int  # Pine confT
    expires_ms: int  # Pine expT
    source: ZoneSource = ZoneSource.SD
    volume_strong: bool = False
    variant: str = ""

    #: Pine bar_index v momente vzniku - gap sa smie hľadať len za ním.
    created_bar_index: int = 0
    #: čas baru grafu, na ktorom zóna vznikla (Pine `time` pri `newZone`).
    #: Nie je to `created_ms` - ten ukazuje na základovú sviečku v minulosti.
    detected_ms: int = 0

    # ---- stav životného cyklu (Pine zStateA a spol.) --------------------- #
    state: int = 0
    used: bool = False
    touched: bool = False
    touched_bar_index: int | None = None
    state_bar_index: int | None = None
    state_time_ms: int | None = None

    # ---- nájdený imbalance / pattern (Pine zImb*A) ----------------------- #
    imb_body_top: float | None = None
    imb_body_bot: float | None = None
    imb_open: float | None = None
    imb_high: float | None = None
    imb_low: float | None = None
    imb_bar_index: int | None = None

    # ---- order (Pine zS4OrderedA, zOrderSlA, zFilledA, zPendingInvalidA) -- #
    order_sl: float | None = None
    ordered: bool = False
    filled: bool = False
    pending_invalid: bool = False
    entry_done: bool = False
    #: len na kreslenie — TP/SL boxy sa po zavretí obchodu utnú práve raz.
    trade_boxes_closed: bool = False

    @property
    def order_id(self) -> str:
        """Pine `"LONG_" + uidStr` / `"SHORT_" + uidStr`."""
        return f"{'LONG' if self.direction is Direction.LONG else 'SHORT'}_{self.uid}"

    def contains(self, price: float) -> bool:
        return self.bot <= price <= self.top

    def is_expired(self, ts_ms: int) -> bool:
        return ts_ms >= self.expires_ms

    @property
    def height(self) -> float:
        return self.top - self.bot

    @property
    def color(self) -> str:
        return zone_color(int(self.direction), self.volume_strong)

    @property
    def pre_box_id(self) -> str:
        return f"z{self.uid}.pre"

    @property
    def post_box_id(self) -> str:
        return f"z{self.uid}.post"

    def resize_on_invalidation(self, now_ms: int) -> list[DrawUpdate]:
        """Pine `resizeZoneOnInvalidation` (riadok 1478) — oba boxy končia TERAZ.

        Bez toho box "visí" v pôvodnej šírke až po `expT`, hoci zóna už dávno
        neplatí. Pine to volá na každej ceste invalidácie aj pri expirácii.
        """
        return [
            DrawUpdate(self.pre_box_id, "x2_ms", now_ms),
            DrawUpdate(self.post_box_id, "x2_ms", now_ms),
        ]

    def recolor(self, color: str) -> list[DrawUpdate]:
        """Pine `box.set_border_color` + `set_bgcolor` (riadky 1577–1580 a spol.).

        Zóna sa prefarbí, keď ju potvrdí pin bar, engulfing alebo imbalance.
        """
        return [
            DrawUpdate(self.pre_box_id, "border_color", with_alpha(color, 15)),
            DrawUpdate(self.post_box_id, "border_color", with_alpha(color, 15)),
            DrawUpdate(self.post_box_id, "fill_color", with_alpha(color, 85)),
        ]

    def boxes(self, step_ms: int) -> list[DrawBox]:
        """Dva boxy, ktoré Pine kreslí pri vzniku zóny (riadky 651–657).

        `pre` je formácia (bodkovaný obrys, bez výplne) od základovej sviečky po
        potvrdenie, `post` je potvrdená zóna (plná výplň) až po expiráciu.
        Neskoršie zmeny idú cez `resize_on_invalidation()` / `recolor()`.
        """
        border = self.color

        pre_right = self.confirmed_ms if self.confirmed_ms > self.created_ms else self.created_ms + step_ms
        pre_right = min(pre_right, self.expires_ms)

        post_left = self.confirmed_ms
        post_right = self.expires_ms if self.expires_ms > post_left else post_left + step_ms

        return [
            DrawBox(
                kind=DrawKind.SD_ZONE_PRE,
                x1_ms=self.created_ms,
                y1=self.top,
                x2_ms=pre_right,
                y2=self.bot,
                border_color=with_alpha(border, 15),
                fill_color=None,
                border_style=LineStyle.DOTTED,
                obj_id=self.pre_box_id,
                zone_uid=self.uid,
            ),
            DrawBox(
                kind=DrawKind.SD_ZONE_POST,
                x1_ms=post_left,
                y1=self.top,
                x2_ms=post_right,
                y2=self.bot,
                border_color=with_alpha(border, 15),
                fill_color=with_alpha(border, 85),
                border_style=LineStyle.SOLID,
                obj_id=self.post_box_id,
                zone_uid=self.uid,
            ),
        ]


class ZoneBook:
    """Evidencia zón — poradie vzniku, strop počtu, deduplikácia.

    Pine drží zóny v paralelných poliach a pri prekročení `maxSdZonesEff` odstrelí
    najstaršiu cez `array.shift`. Tu je to jeden zoznam s tým istým správaním.
    """

    def __init__(self, cfg: IBSConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.step_ms = chart_tf_minutes * 60_000
        self.zone_valid_ms = int(cfg.zoneValidHours * 3_600_000)
        self.max_zones = min(cfg.maxSdZones, MAX_ZONES_HARD_CAP)

        self.zones: list[Zone] = []
        self._next_uid = 0
        #: Pine `lastDrawT0` — tá istá základová sviečka nesmie založiť zónu dvakrát.
        self._last_base_ms: int | None = None
        self.evicted = 0

    def __len__(self) -> int:
        return len(self.zones)

    def create_from_pattern(self, pattern: SdPattern, now_ms: int) -> Zone | None:
        """Pine riadky 638–660. Vráti novú zónu, alebo `None` ak sa nemá vytvoriť."""
        if not self.cfg.enableZoneDetection:
            return None
        if self._last_base_ms is not None and pattern.base_ms == self._last_base_ms:
            return None  # tá istá základová sviečka - Pine `lastDrawT0` dedup

        mode = self.cfg.snapMode
        left = snap_time(pattern.base_ms, self.step_ms, mode)
        expires = left + self.zone_valid_ms

        confirm = snap_time(pattern.confirm_ms or now_ms, self.step_ms, mode)
        confirm = max(confirm, left)
        confirm = min(confirm, expires)

        zone = Zone(
            uid=self._next_uid,
            direction=pattern.direction,
            top=pattern.top,
            bot=pattern.bot,
            created_ms=left,
            confirmed_ms=confirm,
            expires_ms=expires,
            source=ZoneSource.SD,
            volume_strong=pattern.volume_strong,
            variant=pattern.variant,
            detected_ms=now_ms,
        )
        self._next_uid += 1
        self._last_base_ms = pattern.base_ms

        self.zones.append(zone)
        while len(self.zones) > self.max_zones:
            self.zones.pop(0)
            self.evicted += 1
        return zone

    def create_raw(
        self, direction: Direction, top: float, bot: float, now_ms: int, source: ZoneSource
    ) -> Zone:
        """Pine `f_pushZone` volané z S/R (riadok 931) a likvidity (1206, 1247).

        Na rozdiel od SD zóny tu nie je pattern ani základová sviečka — zóna začína
        rovno na aktuálnom bare a platnosť sa počíta od neho.
        """
        zone = Zone(
            uid=self._next_uid,
            direction=direction,
            top=top,
            bot=bot,
            created_ms=now_ms,
            confirmed_ms=now_ms,
            expires_ms=now_ms + self.zone_valid_ms,
            source=source,
            detected_ms=now_ms,
        )
        self._next_uid += 1
        self.zones.append(zone)
        while len(self.zones) > self.max_zones:
            self.zones.pop(0)
            self.evicted += 1
        return zone

    def active(self, ts_ms: int) -> list[Zone]:
        return [z for z in self.zones if not z.is_expired(ts_ms)]

    def drop_expired(self, ts_ms: int) -> list[Zone]:
        """Odstráni expirované zóny a vráti ich (adaptér podľa toho zmaže kresbu)."""
        expired = [z for z in self.zones if z.is_expired(ts_ms)]
        if expired:
            self.zones = [z for z in self.zones if not z.is_expired(ts_ms)]
        return expired
