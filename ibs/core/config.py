"""`IBSConfig` — 111 zo 115 vstupov Pine stratégie ako jeden dataclass.

Názvy polí sú **zámerne zhodné s Pine identifikátormi** (camelCase), nie snake_case.
Dôvod: pri hľadaní odchýlky sa to isté meno grepne v `imbalance_strategy_FULL.pine`
aj tu, a JSON profil sedí s tým, čo vidno v TradingView paneli. Vlastný nový kód
(`InstrumentSpec`, `SizeSpec`, engine) používa bežný Python štýl.

Zdroj hodnôt a rozsahov: `imbalance_strategy_FULL.pine`, sekcia INPUTS (riadky 41–219).
Nastavenia z grafu, ktoré sa líšia od Pine defaultov, sú v `docs/tv_settings_2026-09-03.md`.

**PickMyTrade sa neportuje** (rozhodnutie z 2026-09-04). Vypadlo teda päť Pine vstupov:
`pmtToken`, `pmtAccountId`, `pmtStratName`, `pmtMarketOrderType` a `trailFreqPct`
(ten bol podľa vlastného Pine tooltipu použiteľný LEN pre PickMyTrade — `strategy.exit`
v TradingView pre neho nemá ekvivalent). Zoznam je aj v `ibs/tests/test_pine_parity.py`,
aby test parity vedel, že chýbajú zámerne.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .types import (
    INSTRUMENTS,
    InstrumentSpec,
    OrderType,
    PanelPos,
    SizeSpec,
    SizeUnit,
    SnapMode,
    TradeDirection,
)

__all__ = [
    "IBSConfig",
    "ConfigError",
    "SIZE_FIELDS",
    "CONSTRAINTS",
    "CONFIG_DIR",
    "load_profile",
    "list_profiles",
]

#: Adresár s JSON profilmi. Profil obsahuje LEN odchýlky od Pine defaultov,
#: takže je čitateľný a diff proti originálu je zrejmý.
CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"


class ConfigError(ValueError):
    """Config je nekonzistentný alebo mimo rozsahu, ktorý Pine povoľuje."""


#: Polia, ktoré sú `SizeSpec`, a ich pôvodná Pine jednotka.
#: Holé číslo v JSON = presné Pine správanie.
SIZE_FIELDS: dict[str, SizeUnit] = {
    # *Points — absolútne cenové body
    "minImbSizePoints": "abs",
    "pbMinRangePoints": "abs",
    "engMinRangePoints": "abs",
    "srClusterPoints": "abs",
    "liqSweepMinWick": "abs",
    "ewMinWavePoints": "abs",
    # *Ticks — násobky syminfo.mintick
    "imbMaxDistTicks": "ticks",
    "state2ConfirmTicks": "ticks",
    "slBufferTicks": "ticks",
}

#: Rozsahy prevzaté z `minval=`/`maxval=` v Pine. Platia pre pôvodnú jednotku;
#: ak je pole prepnuté na `atr`/`pct`, kontroluje sa len nezápornosť.
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "pbWickToBodyRatio": (1.0, 10.0),
    "pbBodyPositionPct": (5, 50),
    "pbMinRangePoints": (0, 200),
    "engMinRangePoints": (0, 200),
    "engSizeAvgLen": (3, 100),
    "engSizeMultiplier": (1.0, 10.0),
    "engTouchWindowBars": (1, 50),
    "trailActivationR": (0.1, 10.0),
    "trailOffsetR": (0.05, 10.0),
    "zoneValidHours": (1, 72),
    "maxSdZones": (10, 999),
    "volSmaLen": (2, 200),
    "volMultiplier": (0.5, 10.0),
    "structureSwingLen": (2, 50),
    "srSwingLen": (2, 100),
    "srClusterPoints": (1, 200),
    "srMinTouches": (1, 10),
    "srMaxLevels": (1, 30),
    "srLookbackDays": (1, 30),
    "srZoneSaturationPct": (5, 100),
    "liqSweepLen": (2, 100),
    "liqSweepMinWick": (0, 100),
    "liqSweepConfirmBars": (1, 20),
    "liqStrengthLen": (5, 300),
    "ewSwingLen": (2, 100),
    "ewMinWavePoints": (1, 1000),
    "ewProjExtendBars": (5, 300),
    "dashboardRows": (1, 6),
    "tradeLogRows": (5, 20),
    "debugTableRows": (1, 8),
    "imbLookback": (1, 50),
    "imbMaxDistTicks": (0, 500),
    "minImbSizePoints": (1, 30),
    "state1MaxBars": (1, 50),
    "state2MaxBars": (1, 50),
    "state2ConfirmTicks": (0, 200),
    "state3MaxBars": (1, 50),
    "state4MaxBars": (1, 50),
    "state5MaxBars": (1, 50),
    "rrRatio": (0.5, 10.0),
    "slLookback": (1, 100),
    "slBufferTicks": (0, 50),
    "maxLossDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "maxDailyWins": (1, 20),
}

#: `zoneDetectionTF` — povolené hodnoty z Pine `options=[...]`.
DETECTION_TFS: tuple[str, ...] = (
    "1", "3", "5", "15", "30", "45", "60", "120", "180", "240", "D",
)


#: Polia, ktoré sa vždy držia ako enum, nie ako holý reťazec.
_ENUM_FIELDS: dict[str, type] = {
    "snapMode": SnapMode,
    "tradeDirection": TradeDirection,
    "pbEngOrderType": OrderType,
    "dashPos": PanelPos,
    "debugPos": PanelPos,
}


def _size(value: float, name: str) -> SizeSpec:
    return SizeSpec(value, SIZE_FIELDS[name])


@dataclass
class IBSConfig:
    """Kompletná konfigurácia stratégie. Defaulty = Pine defaulty, nie nastavenia z grafu."""

    # ---- 🎯 Obchodovanie: entry modely ----------------------------------- #
    enableImbEntry: bool = True
    enablePinBarEntry: bool = False
    enableEngulfingEntry: bool = False
    pbWickToBodyRatio: float = 4.0
    pbBodyPositionPct: float = 20.0
    pbMinRangePoints: SizeSpec = field(default_factory=lambda: _size(2.0, "pbMinRangePoints"))
    engMinRangePoints: SizeSpec = field(default_factory=lambda: _size(2.0, "engMinRangePoints"))
    engSizeAvgLen: int = 10
    engSizeMultiplier: float = 2.0
    engTouchWindowBars: int = 3
    pbEngOrderType: OrderType = OrderType.MARKET

    # ---- 🎯 Obchodovanie: trailing --------------------------------------- #
    enableTrailing: bool = False
    trailActivationR: float = 1.0
    trailOffsetR: float = 0.5

    # ---- ⚙️ Základné nastavenia ------------------------------------------ #
    weekdaysOnly: bool = True
    enableTrading: bool = True
    enableZoneDetection: bool = True
    enableGapDetection: bool = True
    enableSrTrading: bool = False
    enableLqTrading: bool = False
    closeAtSessionEnd: bool = True

    # ---- 🌏 Session 1 (Ázia) --------------------------------------------- #
    sess1On: bool = False
    sess1TZ: str = "Europe/Prague"
    sess1ZoneStartH: int = 1
    sess1ZoneStartM: int = 0
    sess1ZoneEndH: int = 9
    sess1ZoneEndM: int = 0
    sess1TradeStartH: int = 2
    sess1TradeStartM: int = 0
    sess1TradeEndH: int = 5
    sess1TradeEndM: int = 0

    # ---- 📘 Session 2 ----------------------------------------------------- #
    sess2On: bool = True
    sess2TZ: str = "America/New_York"
    sess2ZoneStartH: int = 10
    sess2ZoneStartM: int = 0
    sess2ZoneEndH: int = 11
    sess2ZoneEndM: int = 0
    sess2TradeStartH: int = 10
    sess2TradeStartM: int = 0
    sess2TradeEndH: int = 15
    sess2TradeEndM: int = 45

    # ---- 📙 Session 3 ----------------------------------------------------- #
    sess3On: bool = True
    sess3TZ: str = "Europe/London"
    sess3ZoneStartH: int = 8
    sess3ZoneStartM: int = 0
    sess3ZoneEndH: int = 10
    sess3ZoneEndM: int = 0
    sess3TradeStartH: int = 8
    sess3TradeStartM: int = 0
    sess3TradeEndH: int = 11
    sess3TradeEndM: int = 0

    # ---- 📦 SD zóny ------------------------------------------------------- #
    zoneDetectionTF: str = "5"
    zoneValidHours: int = 6
    maxSdZones: int = 200
    snapMode: SnapMode = SnapMode.FLOOR
    invalidateOnFill: bool = True
    useVolumeFilter: bool = False
    volumeFilterBlockTrading: bool = False
    volSmaLen: int = 20
    volMultiplier: float = 1.5

    # ---- 📈 Market Structure --------------------------------------------- #
    showMarketStructure: bool = True
    structureSwingLen: int = 5
    useStructureFilter: bool = False

    # ---- 📏 Support / Resistance ----------------------------------------- #
    showSR: bool = True
    srSwingLen: int = 10
    srClusterPoints: SizeSpec = field(default_factory=lambda: _size(15.0, "srClusterPoints"))
    srMinTouches: int = 2
    srMaxLevels: int = 10
    srLookbackDays: int = 5
    srZoneSaturationPct: int = 30

    # ---- 💧 Likvidita (sweep) -------------------------------------------- #
    showLiqSweep: bool = True
    liqSweepLen: int = 10
    liqSweepMinWick: SizeSpec = field(default_factory=lambda: _size(5.0, "liqSweepMinWick"))
    liqSweepConfirmBars: int = 2
    liqStrengthLen: int = 50

    # ---- 🌊 Elliott Waves ------------------------------------------------- #
    showElliott: bool = True
    ewSwingLen: int = 8
    ewMinWavePoints: SizeSpec = field(default_factory=lambda: _size(20.0, "ewMinWavePoints"))
    ewShowLabels: bool = True
    ewShowProjection: bool = True
    ewProjExtendBars: int = 40
    ewLineColor: str = "#334155"  # Pine color.rgb(51, 65, 85)

    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showImbalance: bool = True
    showDashboard: bool = True
    dashPos: PanelPos = PanelPos.TOP_RIGHT
    dashboardRows: int = 6
    showTradeLog: bool = False
    tradeLogRows: int = 20
    showDebugTable: bool = False
    debugTableRows: int = 8
    debugPos: PanelPos = PanelPos.BOTTOM_RIGHT

    # ---- 🔧 Pokročilé (časovanie vstupu, SL) ----------------------------- #
    imbLookback: int = 20
    imbMaxDistTicks: SizeSpec = field(default_factory=lambda: _size(100.0, "imbMaxDistTicks"))
    minImbSizePoints: SizeSpec = field(default_factory=lambda: _size(2.5, "minImbSizePoints"))
    state1MaxBars: int = 10
    state2MaxBars: int = 15
    state2ConfirmTicks: SizeSpec = field(default_factory=lambda: _size(1.0, "state2ConfirmTicks"))
    state3MaxBars: int = 1
    state4MaxBars: int = 10  # POZN: Pine ho nikde nepoužíva ("Rezerva")
    state5MaxBars: int = 10
    alertOnState2: bool = False
    alertOnState3: bool = False
    alertOnState4: bool = False

    # ---- 💰 Veľkosť pozície a riziko ------------------------------------- #
    rrRatio: float = 1.0
    slLookback: int = 10
    slBufferTicks: SizeSpec = field(default_factory=lambda: _size(2.0, "slBufferTicks"))
    maxLossDollar: float = 350.0
    maxDailyWins: int = 5
    tradeDirection: TradeDirection = TradeDirection.BOTH

    #: Pine `tickDollarValue`. Engine ho používa len keď je `legacyPineSizing` zapnuté;
    #: inak sa počíta z `InstrumentSpec.point_value`. `check_instrument()` upozorní,
    #: ak nesedí s inštrumentom — presne tá chyba, ktorá na BTCUSD tíško vypla risk limit.
    tickDollarValue: float | None = None

    #: Doslovné Pine sizing správanie vrátane `int()` + `max(1, …)` — teda aj toho, že sa
    #: pri qty < 1 `maxLossDollar` neuplatní. Zapnúť LEN v referenčných profiloch, kde
    #: potrebujeme reprodukovať TradingView backtest 1:1 (golden test).
    legacyPineSizing: bool = False


    # ------------------------------------------------------------------ #
    # Validácia
    # ------------------------------------------------------------------ #

    def __post_init__(self) -> None:
        for name in _ENUM_FIELDS:
            setattr(self, name, getattr(self, name))
        for name in SIZE_FIELDS:
            setattr(self, name, getattr(self, name))
        self.validate()

    def __setattr__(self, name: str, value: object) -> None:
        """Dotypuje enum a `SizeSpec` polia aj pri priradení po vytvorení.

        Bez toho by `cfg.imbMaxDistTicks = 4` nechalo v poli obyčajný int a spadlo
        by to až hlboko v engine na `.resolve(...)` — presne ten druh tichej chyby,
        ktorej sa v tomto porte vyhýbame.
        """
        if name in SIZE_FIELDS:
            value = SizeSpec.parse(value, default_unit=SIZE_FIELDS[name])
        elif name in _ENUM_FIELDS:
            value = _ENUM_FIELDS[name](value)
        object.__setattr__(self, name, value)

    def validate(self) -> None:
        problems = list(self._problems())
        if problems:
            raise ConfigError("Neplatný config:\n  - " + "\n  - ".join(problems))

    def _problems(self) -> Iterable[str]:
        if self.zoneDetectionTF not in DETECTION_TFS:
            yield (
                f"zoneDetectionTF={self.zoneDetectionTF!r} nie je v povolených "
                f"hodnotách {DETECTION_TFS}"
            )

        for name, (lo, hi) in CONSTRAINTS.items():
            raw = getattr(self, name)
            if raw is None:  # napr. tickDollarValue, ktory je volitelny
                continue
            if isinstance(raw, SizeSpec):
                if raw.unit != SIZE_FIELDS[name]:
                    # iná jednotka než Pine — rozsah z Pine tu neplatí
                    if raw.value < 0:
                        yield f"{name} musí byť >= 0, je {raw.value}"
                    continue
                raw = raw.value
            if not (lo <= raw <= hi):
                yield f"{name}={raw} je mimo rozsahu Pine <{lo}, {hi}>"

        for n in (1, 2, 3):
            for kind in ("Zone", "Trade"):
                sh = getattr(self, f"sess{n}{kind}StartH")
                sm = getattr(self, f"sess{n}{kind}StartM")
                eh = getattr(self, f"sess{n}{kind}EndH")
                em = getattr(self, f"sess{n}{kind}EndM")
                for label, h, m in ((f"{kind}Start", sh, sm), (f"{kind}End", eh, em)):
                    if not (0 <= h <= 23):
                        yield f"sess{n}{label}H={h} musí byť 0–23"
                    if not (0 <= m <= 59):
                        yield f"sess{n}{label}M={m} musí byť 0–59"
                if (sh, sm) == (eh, em):
                    yield f"sess{n} {kind} okno má nulovú dĺžku ({sh:02d}:{sm:02d})"

        if not (self.enableImbEntry or self.enablePinBarEntry or self.enableEngulfingEntry):
            yield "nie je zapnutý žiadny entry model — stratégia by nikdy neobchodovala"

        if not (self.enableZoneDetection or self.enableSrTrading or self.enableLqTrading):
            yield "nie je zapnutý žiadny zdroj zón — stratégia by nikdy neobchodovala"

        if not (self.sess1On or self.sess2On or self.sess3On):
            yield "nie je zapnutá žiadna session — stratégia by nikdy neobchodovala"

        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue (Pine ho v tom vzorci používa)"

        if self.trailOffsetR > self.trailActivationR:
            yield (
                f"trailOffsetR={self.trailOffsetR} > trailActivationR={self.trailActivationR}: "
                "trailing by pri aktivácii posunul SL pod vstup"
            )

    # ------------------------------------------------------------------ #
    # Krížová kontrola s inštrumentom
    # ------------------------------------------------------------------ #

    def position_qty(self, inst: InstrumentSpec, risk_amount: float, sl_distance: float) -> float:
        """Veľkosť pozície — jediné miesto, kde sa rozhoduje medzi Pine a opraveným vzorcom."""
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def check_instrument(self, inst: InstrumentSpec) -> list[str]:
        """Vráti varovania (nie chyby) k dvojici config × inštrument.

        Chytá presne tie tiché chyby, ktoré sú popísané v ARCHITECTURE_port.md §3b/§3c:
        MNQ hodnota `tickDollarValue` na krypte, absolútne „points" na inom inštrumente
        a volume filter na forexe.
        """
        warnings: list[str] = []

        if self.tickDollarValue is not None:
            expected = inst.tick_dollar_value
            if abs(self.tickDollarValue - expected) > 1e-9:
                warnings.append(
                    f"tickDollarValue={self.tickDollarValue} nesedí s {inst.symbol} "
                    f"(tick_size {inst.tick_size} × point_value {inst.point_value} = {expected}). "
                    "Bez legacyPineSizing sa pole ignoruje; s ním počíta zle."
                )

        if self.useVolumeFilter and not inst.has_real_volume:
            warnings.append(
                f"useVolumeFilter je zapnutý, ale {inst.symbol} nemá reálny volume "
                "(len tick volume) — filter bude nespoľahlivý."
            )

        if self.legacyPineSizing and self.maxLossDollar > 0 and self.tickDollarValue:
            # Pri legacy vzorci padne qty na 1 hneď, ako SL prekročí túto vzdialenosť —
            # od nej vyššie sa `maxLossDollar` fakticky neuplatní.
            breakeven_sl = self.maxLossDollar / self.tickDollarValue * inst.tick_size
            warnings.append(
                f"legacyPineSizing na {inst.symbol}: pri SL vzdialenosti nad "
                f"{breakeven_sl:g} vyjde qty=1 a limit rizika sa neuplatní — presne to robil "
                "TradingView. Pre reálne obchodovanie legacyPineSizing vypni."
            )

        if inst.venue not in ("CME", "test"):
            abs_fields = [n for n in SIZE_FIELDS if getattr(self, n).unit == "abs"]
            if abs_fields:
                warnings.append(
                    f"{', '.join(sorted(abs_fields))} sú v absolútnych cenových bodoch — tie hodnoty "
                    f"sú ladené na MNQ a na {inst.symbol} nemusia dávať zmysel; zváž unit='atr'."
                )

        return warnings

    # ------------------------------------------------------------------ #
    # Serializácia
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IBSConfig":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known - {"_comment", "_instrument"}
        if unknown:
            raise ConfigError(f"neznáme kľúče v configu: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json(cls, path: str | Path) -> "IBSConfig":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, SizeSpec):
                out[f.name] = v.value if v.unit == SIZE_FIELDS[f.name] else v.to_json()
            elif isinstance(v, Enum):
                out[f.name] = v.value
            else:
                out[f.name] = v
        return out

    def to_json(self, path: str | Path, *, comment: str | None = None) -> None:
        data = self.to_dict()
        if comment:
            data = {"_comment": comment, **data}
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")


# --------------------------------------------------------------------------- #
# Profily
# --------------------------------------------------------------------------- #


def list_profiles() -> list[str]:
    """Mená dostupných JSON profilov v `ibs/configs/`."""
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json"))


def load_profile(name: str | Path) -> tuple[IBSConfig, InstrumentSpec]:
    """Načíta profil podľa mena (`"mnq_3m"`) alebo cesty a vráti config + inštrument.

    Profil obsahuje len odchýlky od Pine defaultov plus kľúč `_instrument`,
    ktorý ukazuje do `types.INSTRUMENTS`.
    """
    path = Path(name)
    if not path.suffix:
        path = CONFIG_DIR / f"{name}.json"
    if not path.exists():
        raise ConfigError(f"profil {path} neexistuje; dostupné: {list_profiles()}")

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    inst_key = data.get("_instrument")
    if inst_key is None:
        raise ConfigError(f"{path.name}: chýba kľúč '_instrument'")
    if inst_key not in INSTRUMENTS:
        raise ConfigError(
            f"{path.name}: neznámy _instrument {inst_key!r}; známe: {sorted(INSTRUMENTS)}"
        )

    return IBSConfig.from_dict(data), INSTRUMENTS[inst_key]
