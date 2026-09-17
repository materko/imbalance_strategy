"""`IBSConfig` — 99 zo 115 vstupov Pine stratégie ako jeden dataclass.

Názvy polí sú **zámerne zhodné s Pine identifikátormi** (camelCase), nie snake_case.
Dôvod: pri hľadaní odchýlky sa to isté meno grepne v `tradebot/strategies/ibs/docs/sources/imbalance_strategy_FULL.pine`
aj tu, a JSON profil sedí s tým, čo vidno v TradingView paneli. Vlastný nový kód
(`InstrumentSpec`, `SizeSpec`, engine) používa bežný Python štýl.

Zdroj hodnôt a rozsahov: `tradebot/strategies/ibs/docs/sources/imbalance_strategy_FULL.pine`, sekcia INPUTS (riadky 41–219).
Nastavenia z grafu, ktoré sa líšia od Pine defaultov, sú v `docs/tv_settings_2026-09-03.md`.

**PickMyTrade sa neportuje** (rozhodnutie z 2026-09-04). Vypadlo teda päť Pine vstupov:
`pmtToken`, `pmtAccountId`, `pmtStratName`, `pmtMarketOrderType` a `trailFreqPct`
(ten bol podľa vlastného Pine tooltipu použiteľný LEN pre PickMyTrade — `strategy.exit`
v TradingView pre neho nemá ekvivalent).

**Alerty a tabuľky na graf TradingView sa neportujú** (rozhodnutie z 2026-09-17): ďalších
jedenásť vstupov v `PINE_DISPLAY_INPUTS` nižšie. Staré profily a behy ich nesú, preto sú
aj v `RETIRED_FIELDS`.

Oba zoznamy sú v `REMOVED_INPUTS` (`meta.py`), aby test parity
(`tester/tests/test_pine_parity.py`) vedel, že chýbajú zámerne.
"""

from __future__ import annotations

from pathlib import Path

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Iterable

from tradebot.core.config import ConfigError, StrategyConfig, list_profiles, load_profile

from tradebot.core.types import (
    Direction,
    InstrumentSpec,
    OrderType,
    SizeSpec,
    SizeUnit,
    SnapMode,
)

__all__ = [
    "IBSConfig",
    "ConfigError",
    "TradeDirection",
    "IndicatorAction",
    "INDICATOR_RULES",
    "PriceSource",
    "timeframe_option_minutes",
    "SIZE_FIELDS",
    "PORT_ONLY_FIELDS",
    "PINE_DISPLAY_INPUTS",
    "RETIRED_FIELDS",
    "CONSTRAINTS",
    "CONFIG_DIR",
    "load_profile",
    "list_profiles",
]

#: Adresár s JSON profilmi IBS. Profil obsahuje LEN odchýlky od Pine defaultov,
#: takže je čitateľný a diff proti originálu je zrejmý.
#: Profily stratégie ležia pri nej, aby bol balík sebestačný.
CONFIG_DIR = Path(__file__).resolve().parent / "configs"


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
    # rozšírenie portu (nie je v Pine) — percento z ceny
    "minSlDistance": "pct",
}

#: Polia, ktoré Pine nemá — rozšírenia portu. Test parity ich pozná menovite.
PORT_ONLY_FIELDS: frozenset[str] = frozenset({
    "atrLen", "legacyPineSizing", "leverage", "minSlDistance",
    # smer obchodov podľa indikátorov (`tradeDirection = Indicator`) — ta/trend.py
    "indSupertrend", "stTimeframe", "stAtrPeriod", "stSource", "stMultiplier", "stChangeAtr",
    "stShowSignals", "stHighlighting",
    "indAdx", "adxTimeframe", "adxDiLength", "adxSmoothing", "adxThreshold", "adxShowState",
    "ruleStUp", "ruleStDown", "ruleAdxUp", "ruleAdxDown", "ruleAdxSide",
    "ruleStUpAdxUp", "ruleStUpAdxSide", "ruleStUpAdxDown",
    "ruleStDownAdxUp", "ruleStDownAdxSide", "ruleStDownAdxDown",
})

#: Zrušené polia (staré profily a behy ich nesú). `directionIndicator` bol pokusný výber
#: jedného indikátora pred `indSupertrend`/`indAdx`; všetky uložené behy majú "Supertrend"
#: = dnešný default.
#: Pine vstupy len pre TradingView — alerty (`alertOnState*`) a tabuľky kreslené na graf
#: (dashboard, tabuľka obchodov, diagnostický panel). Port ich nečíta: notifikácie rieši
#: Freqtrade sám a obchody aj dôvody výstupu ukazuje webapp. Do 2026-09-17 boli v configu
#: kvôli parite panela (skryté vo formulári); Pine ich má ďalej, preto sú aj v
#: `REMOVED_INPUTS` (`meta.py`) medzi vedome neportovanými vstupmi.
PINE_DISPLAY_INPUTS: frozenset[str] = frozenset({
    "alertOnState2", "alertOnState3", "alertOnState4",
    "showDashboard", "dashPos", "dashboardRows",
    "showTradeLog", "tradeLogRows",
    "showDebugTable", "debugTableRows", "debugPos",
})

RETIRED_FIELDS: dict[str, str] = {
    "directionIndicator": "nahradené indSupertrend/indAdx (hodnota Supertrend = default)",
    **{name: "Pine vstup len pre alerty/dashboard/debug, port ho nečíta"
       for name in sorted(PINE_DISPLAY_INPUTS)},
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
    "atrLen": (1, 500),
    "leverage": (1.0, 125.0),
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
    "stAtrPeriod": (1, 500),
    "stMultiplier": (0.1, 50.0),
    "adxDiLength": (1, 500),
    "adxSmoothing": (1, 500),
    "adxThreshold": (0.0, 100.0),
}

#: `zoneDetectionTF` — povolené hodnoty z Pine `options=[...]`.
DETECTION_TFS: tuple[str, ...] = (
    "1", "3", "5", "15", "30", "45", "60", "120", "180", "240", "D",
)


#: Polia, ktorých hodnota je voľba z `DETECTION_TFS`.
_TF_FIELDS = frozenset({"zoneDetectionTF", "stTimeframe", "adxTimeframe"})


def timeframe_option_minutes(tf: str) -> int:
    """Hodnota z `DETECTION_TFS` v minútach (`"D"` = 1440)."""
    return 1440 if str(tf) == "D" else int(tf)


class TradeDirection(str, Enum):
    """Pine `tradeDirection` a navyše `Indicator` — smer určujú zvolené indikátory a pravidlá.

    Jadro má vlastný `TradeDirection` bez `Indicator` (používajú ho iné stratégie), preto
    IBS drží svoj; hodnoty prvých troch sú zhodné, profily sa teda nemenia.
    """

    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"
    INDICATOR = "Indicator"

    def allows(self, d: Direction) -> bool:
        """Pevný smer; pri `INDICATOR` rozhoduje až brána indikátora (`DirectionGate`)."""
        if self is TradeDirection.LONG_ONLY:
            return d is Direction.LONG
        if self is TradeDirection.SHORT_ONLY:
            return d is Direction.SHORT
        return True


class IndicatorAction(str, Enum):
    """Čo robiť pri danej kombinácii stavov indikátorov (`rule*` polia)."""

    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"
    NO_TRADE = "No trade"

    def allows(self, d: Direction) -> bool:
        if self is IndicatorAction.BOTH:
            return True
        if self is IndicatorAction.LONG_ONLY:
            return d is Direction.LONG
        if self is IndicatorAction.SHORT_ONLY:
            return d is Direction.SHORT
        return False


#: Pravidlo pre kombináciu stavov: (Supertrend, ADX) -> pole configu. Stav je `up`/`down`
#: (ADX aj `side` = do strany), `None` = indikátor nie je zaškrtnutý.
INDICATOR_RULES: dict[tuple[str | None, str | None], str] = {
    ("up", None): "ruleStUp",
    ("down", None): "ruleStDown",
    (None, "up"): "ruleAdxUp",
    (None, "down"): "ruleAdxDown",
    (None, "side"): "ruleAdxSide",
    ("up", "up"): "ruleStUpAdxUp",
    ("up", "side"): "ruleStUpAdxSide",
    ("up", "down"): "ruleStUpAdxDown",
    ("down", "up"): "ruleStDownAdxUp",
    ("down", "side"): "ruleStDownAdxSide",
    ("down", "down"): "ruleStDownAdxDown",
}


class PriceSource(str, Enum):
    """Pine `input(hl2, "Source")` — zdroj ceny indikátora."""

    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    HL2 = "hl2"
    HLC3 = "hlc3"
    OHLC4 = "ohlc4"
    HLCC4 = "hlcc4"


#: Polia, ktoré sa vždy držia ako enum, nie ako holý reťazec.
ENUM_FIELDS: dict[str, type] = {
    "snapMode": SnapMode,
    "tradeDirection": TradeDirection,
    "stSource": PriceSource,
    **{name: IndicatorAction for name in INDICATOR_RULES.values()},
    "pbEngOrderType": OrderType,
}


def _size(value: float, name: str) -> SizeSpec:
    return SizeSpec(value, SIZE_FIELDS[name])


@dataclass
class IBSConfig(StrategyConfig):
    """Kompletná konfigurácia stratégie. Defaulty = Pine defaulty, nie nastavenia z grafu."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS
    RETIRED_FIELDS: ClassVar[dict[str, str]] = RETIRED_FIELDS

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

    # ---- 💰 Veľkosť pozície a riziko ------------------------------------- #
    rrRatio: float = 1.0
    slLookback: int = 10
    slBufferTicks: SizeSpec = field(default_factory=lambda: _size(2.0, "slBufferTicks"))
    maxLossDollar: float = 350.0
    maxDailyWins: int = 5
    tradeDirection: TradeDirection = TradeDirection.BOTH

    # ---- 🧭 Smer podľa indikátorov (rozšírenie portu, `tradeDirection = Indicator`) ---- #
    # Zaškrtnuté indikátory dajú stav (hore / dole / do strany) a pravidlo pre tú kombináciu
    # povie, ktorý smer smie zóna obchodovať. Viď ta/trend.py.

    #: Supertrend (TradingView, KivancOzbilgic)
    indSupertrend: bool = True
    #: TF, na ktorom sa Supertrend počíta (skladá sa z barov grafu — musí byť jeho násobkom).
    stTimeframe: str = "60"
    #: Supertrend „ATR Period"
    stAtrPeriod: int = 10
    #: Supertrend „Source"
    stSource: PriceSource = PriceSource.HL2
    #: Supertrend „ATR Multiplier"
    stMultiplier: float = 3.0
    #: Supertrend „Change ATR Calculation Method ?" — True = RMA (`atr()`), False = SMA z TR
    stChangeAtr: bool = True
    #: Supertrend „Show Buy/Sell Signals ?" — štítky Buy/Sell na grafe pri otočení trendu
    stShowSignals: bool = True
    #: Supertrend „Highlighter On/Off ?" — výplň medzi čiarou a cenou
    stHighlighting: bool = True

    #: ADX/DMI (TradingView „Directional Movement Index")
    indAdx: bool = False
    #: TF, na ktorom sa ADX/DMI počíta (násobok TF grafu)
    adxTimeframe: str = "60"
    #: DMI „DI Length"
    adxDiLength: int = 14
    #: DMI „ADX Smoothing"
    adxSmoothing: int = 14
    #: ADX pod touto hodnotou = trh do strany; inak smer podľa +DI / −DI
    adxThreshold: float = 20.0
    #: podfarbenie grafu behu podľa stavu ADX (hore / dole / do strany)
    adxShowState: bool = True

    # Pravidlá: čo robiť pri kombinácii stavov. Len Supertrend / len ADX / oba.
    ruleStUp: IndicatorAction = IndicatorAction.LONG_ONLY
    ruleStDown: IndicatorAction = IndicatorAction.SHORT_ONLY
    ruleAdxUp: IndicatorAction = IndicatorAction.LONG_ONLY
    ruleAdxDown: IndicatorAction = IndicatorAction.SHORT_ONLY
    ruleAdxSide: IndicatorAction = IndicatorAction.NO_TRADE
    ruleStUpAdxUp: IndicatorAction = IndicatorAction.LONG_ONLY
    ruleStUpAdxSide: IndicatorAction = IndicatorAction.NO_TRADE
    ruleStUpAdxDown: IndicatorAction = IndicatorAction.NO_TRADE
    ruleStDownAdxUp: IndicatorAction = IndicatorAction.NO_TRADE
    ruleStDownAdxSide: IndicatorAction = IndicatorAction.NO_TRADE
    ruleStDownAdxDown: IndicatorAction = IndicatorAction.SHORT_ONLY

    #: Pine `tickDollarValue`. Engine ho používa len keď je `legacyPineSizing` zapnuté;
    #: inak sa počíta z `InstrumentSpec.point_value`. `check_instrument()` upozorní,
    #: ak nesedí s inštrumentom — presne tá chyba, ktorá na BTCUSD tíško vypla risk limit.
    tickDollarValue: float | None = None

    #: Doslovné Pine sizing správanie vrátane `int()` + `max(1, …)` — teda aj toho, že sa
    #: pri qty < 1 `maxLossDollar` neuplatní. Zapnúť LEN v referenčných profiloch, kde
    #: potrebujeme reprodukovať TradingView backtest 1:1 (golden test).
    legacyPineSizing: bool = False

    #: Dĺžka ATR pre parametre zadané v jednotke `atr`. V Pine skripte ATR nie je —
    #: je to rozšírenie portu (ARCHITECTURE_port.md §3b), aby sa prahy naladené
    #: v bodoch na MNQ dali preniesť na inštrument s inou cenovou škálou.
    atrLen: int = 14

    #: Minimálna vzdialenosť SL od vstupu, inak sa obchod preskočí („SL PRILIS TESNY").
    #: Pine to nemá — rozšírenie portu kvôli poplatkom: hrubý zisk obchodu rastie
    #: s veľkosťou R, poplatok je vždy percento z nominálu, takže obchody s tesným SL
    #: majú najhorší pomer edge k poplatku. Na BTCUSDT.P (NY profil, 5 rokov) mal
    #: najtesnejší kvartil (SL ~0,12 % ceny) break-even ≈ 0 a WR 18 %, kým zvyšok
    #: 0,04–0,17 %. Defaultne 0 = vypnuté, aby ostala parita s TradingView.
    minSlDistance: SizeSpec = field(default_factory=lambda: _size(0.0, "minSlDistance"))

    #: Páka. Pine ju nepozná — strategy tester v TradingView marže nerieši a nechá
    #: otvoriť ľubovoľne veľkú pozíciu. Vo Freqtrade je to limit, ktorý sa NAOZAJ
    #: uplatní: risk-based sizing z `maxLossDollar` chce na BTC pri tesnom SL
    #: notional v státisícoch USDT, takže pri páke 1 sa stake oreže a `maxLossDollar`
    #: sa vôbec neuplatní. Viď docs/GOLDEN_binance_2026-08-24.md.
    leverage: float = 1.0


    def __setattr__(self, name: str, value: object) -> None:
        """TF polia sú reťazce z `DETECTION_TFS`, ale `--set stTimeframe=60` pošle číslo."""
        if name in _TF_FIELDS and isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(int(value)) if float(value).is_integer() else str(value)
        super().__setattr__(name, value)

    # ------------------------------------------------------------------ #
    # Validácia
    # ------------------------------------------------------------------ #

    def _problems(self) -> Iterable[str]:
        """Pravidlá IBS; rozsahy z `CONSTRAINTS` kontroluje báza."""
        for name in ("stTimeframe", "adxTimeframe"):
            if getattr(self, name) not in DETECTION_TFS:
                yield f"{name}={getattr(self, name)!r} nie je v povolených hodnotách {DETECTION_TFS}"

        if self.tradeDirection is TradeDirection.INDICATOR and not (self.indSupertrend or self.indAdx):
            yield "tradeDirection=Indicator, ale nie je zaškrtnutý žiadny indikátor (indSupertrend, indAdx)"

        if self.zoneDetectionTF not in DETECTION_TFS:
            yield (
                f"zoneDetectionTF={self.zoneDetectionTF!r} nie je v povolených "
                f"hodnotách {DETECTION_TFS}"
            )

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

    # Serializácia a profily: `StrategyConfig` v tradebot/core/config.py.
    # `load_profile`/`list_profiles` sú tu len re-exportované pre spätnú kompatibilitu.
