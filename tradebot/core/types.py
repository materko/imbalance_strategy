"""Základné dátové typy spoločného jadra.

Nič v tomto module nesmie importovať Freqtrade ani MultiCharts — jadro je
platformovo neutrálne (viď docs/ARCHITECTURE_port.md §2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Literal

__all__ = [
    "Bar",
    "HTFWindow",
    "Direction",
    "TradeDirection",
    "SnapMode",
    "OrderType",
    "PanelPos",
    "SizeUnit",
    "SizeSpec",
    "InstrumentSpec",
    "MNQ",
    "BTCUSD_COINBASE",
    "BTCUSDT_BINANCE",
    "INSTRUMENTS",
]


# --------------------------------------------------------------------------- #
# Bary
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Bar:
    """Jedna sviečka. `time` je čas OTVORENIA baru v ms epoch (ako Pine `time`)."""

    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def body_top(self) -> float:
        return max(self.open, self.close)

    @property
    def body_bottom(self) -> float:
        return min(self.open, self.close)

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def is_up(self) -> bool:
        return self.close >= self.open


@dataclass(frozen=True, slots=True)
class HTFWindow:
    """Okno posledných uzavretých barov detekčného TF (`zoneDetectionTF`).

    Pine si ho ťahá jedným `request.security(...)` na riadku 338 súboru
    pine/imbalance_strategy_FULL.pine, s offsetom ``[1]``..``[4]`` a ``lookahead_off``.
    ``bars[0]`` je teda Pine ``[1]`` — posledný UZAVRETÝ HTF bar, nie ten rozpracovaný.
    Preto tu nikdy nedochádza k repaintu.
    """

    REQUIRED_BARS: ClassVar[int] = 4

    bars: tuple[Bar, ...]  # dĺžka 4: Pine [1], [2], [3], [4]
    vol_sma: float  # ta.sma(volume, volSmaLen)[1]

    def __post_init__(self) -> None:
        if len(self.bars) != self.REQUIRED_BARS:
            raise ValueError(
                f"HTFWindow potrebuje presne {self.REQUIRED_BARS} barov, dostal {len(self.bars)}"
            )


def htf_window_opens(ts_ms: int, chart_tf_ms: int, htf_ms: int, count: int = HTFWindow.REQUIRED_BARS) -> list[int]:
    """Otváracie časy HTF barov, ktoré Pine `request.security` vidí na danom bare grafu.

    `ts_ms` je OTVÁRACÍ čas baru grafu; Pine vyhodnocuje bar pri jeho uzavretí, teda
    v čase ``ts_ms + chart_tf_ms``. S ``lookahead_off`` je vtedy "aktuálnym" HTF barom
    v security ten, ktorý sa naposledy UZAVREL::

        newest_close = floor(close_ms / htf_ms) * htf_ms      ->  open = newest_close - htf_ms

    Výraz v security (riadok 338 Pine) má navyše offset ``[1]``, takže ``bars[0]``
    je ešte o jeden HTF bar dozadu — spolu ``- 2 * htf_ms``.

    Keď sa mriežky neprekrývajú (3m graf / 5m detekcia), tento posun NIE JE konštantný
    voči ``ts_ms // htf_ms``: na bare 12:00 dá okno končiace 11:50, na 12:06 okno
    končiace 12:00 a na 12:12 okno končiace 12:05. Práve preto sa okno nesmie počítať
    z otváracieho času baru.
    """
    close_ms = ts_ms + chart_tf_ms
    newest = (close_ms // htf_ms) * htf_ms - 2 * htf_ms
    return [newest - i * htf_ms for i in range(count)]


# --------------------------------------------------------------------------- #
# Enumy (hodnoty sú zhodné s Pine reťazcami, aby sa dali čítať priamo z JSON)
# --------------------------------------------------------------------------- #


class Direction(int, Enum):
    """Smer zóny/obchodu. Hodnoty kopírujú Pine `typ` (+1 = demand/long)."""

    LONG = 1
    SHORT = -1

    @property
    def opposite(self) -> "Direction":
        return Direction.SHORT if self is Direction.LONG else Direction.LONG


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"

    def allows(self, d: Direction) -> bool:
        if self is TradeDirection.BOTH:
            return True
        if self is TradeDirection.LONG_ONLY:
            return d is Direction.LONG
        return d is Direction.SHORT


class SnapMode(str, Enum):
    OFF = "Off"
    FLOOR = "Floor"
    CEIL = "Ceil"
    ROUND = "Round"


class OrderType(str, Enum):
    LIMIT = "Limit"
    MARKET = "Market"


class PanelPos(str, Enum):
    TOP_RIGHT = "Top Right"
    TOP_LEFT = "Top Left"
    BOTTOM_RIGHT = "Bottom Right"
    BOTTOM_LEFT = "Bottom Left"


# --------------------------------------------------------------------------- #
# Veľkosti závislé od inštrumentu
# --------------------------------------------------------------------------- #

SizeUnit = Literal["abs", "ticks", "atr", "pct"]
_SIZE_UNITS: frozenset[str] = frozenset(("abs", "ticks", "atr", "pct"))


@dataclass(frozen=True, slots=True)
class SizeSpec:
    """Veľkosť v cenovom priestore, ktorá vie byť prenositeľná medzi inštrumentmi.

    Pine má tieto parametre zadrátované v absolútnych bodoch alebo tickoch, čo
    nefunguje naprieč inštrumentmi: ``minImbSizePoints = 2.5`` je na MNQ zmysluplných
    ~$5, na BTCUSD @ 80 000 to je 0.003 % a na EURUSD úplný nezmysel.

    - ``abs``   — presné Pine správanie pre ``*Points`` inputy (cenové body)
    - ``ticks`` — presné Pine správanie pre ``*Ticks`` inputy (× ``tick_size``)
    - ``atr``   — násobok ATR, jediná naozaj prenositeľná jednotka
    - ``pct``   — percento z ceny, praktické na crypte
    """

    value: float
    unit: SizeUnit = "abs"

    def __post_init__(self) -> None:
        if self.unit not in _SIZE_UNITS:
            raise ValueError(f"neznáma jednotka {self.unit!r}, povolené: {sorted(_SIZE_UNITS)}")
        if self.value < 0:
            raise ValueError(f"SizeSpec.value nesmie byť záporná, dostal {self.value}")

    def resolve(self, inst: "InstrumentSpec", price: float = 0.0, atr: float = 0.0) -> float:
        """Prepočíta na vzdialenosť v cene daného inštrumentu."""
        if self.unit == "abs":
            return self.value
        if self.unit == "ticks":
            return self.value * inst.tick_size
        if self.unit == "atr":
            return self.value * atr
        return self.value / 100.0 * price

    # -- serializácia ------------------------------------------------------- #

    @classmethod
    def parse(cls, raw: object, *, default_unit: SizeUnit = "abs") -> "SizeSpec":
        """Prijme holé číslo (→ ``default_unit``) alebo ``{"value": …, "unit": …}``.

        Holé číslo teda znamená presne to, čo robí Pine — vďaka tomu je JSON profil
        odvodený priamo z TradingView nastavení bit-identický s originálom.
        """
        if isinstance(raw, SizeSpec):
            return raw
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return cls(float(raw), default_unit)
        if isinstance(raw, dict):
            if "value" not in raw:
                raise ValueError(f"SizeSpec dict musí mať kľúč 'value': {raw!r}")
            unknown = set(raw) - {"value", "unit"}
            if unknown:
                raise ValueError(f"SizeSpec dict má neznáme kľúče: {sorted(unknown)}")
            return cls(float(raw["value"]), raw.get("unit", default_unit))
        raise TypeError(f"SizeSpec nevie spracovať {type(raw).__name__}: {raw!r}")

    def to_json(self) -> dict[str, object]:
        return {"value": self.value, "unit": self.unit}


@dataclass(frozen=True, slots=True)
class InstrumentSpec:
    """Vlastnosti inštrumentu, ktoré Pine berie zo `syminfo.*`.

    Hodnoty sa v adaptéroch čítajú z platformy, nezadávajú sa ručne:
      - MultiCharts: ``tick_size = MinMove / PriceScale``, ``point_value = BigPointValue``
      - Freqtrade:   ``exchange.markets[pair]['precision'] / ['limits']``
    Presety nižšie sú len fallback pre testy a offline prácu.
    """

    symbol: str
    venue: str
    tick_size: float
    point_value: float  # $ za pohyb ceny o 1.0, na 1 kontrakt/jednotku
    qty_step: float
    min_qty: float
    has_real_volume: bool = True
    quote_currency: str = "USD"

    def __post_init__(self) -> None:
        for field in ("tick_size", "point_value", "qty_step", "min_qty"):
            if getattr(self, field) <= 0:
                raise ValueError(f"InstrumentSpec.{field} musí byť > 0")

    # -- odvodené ----------------------------------------------------------- #

    @property
    def tick_dollar_value(self) -> float:
        """Pine `tickDollarValue` pre tento inštrument — na krížovú kontrolu configu."""
        return self.tick_size * self.point_value

    def round_price(self, price: float) -> float:
        return round(price / self.tick_size) * self.tick_size

    def round_qty(self, qty: float) -> float:
        """Zaokrúhli nadol na `qty_step` a podrž `min_qty`.

        Pine tu má ``int(math.max(1, math.floor(...)))``, čo je správne pre futures
        a akcie, ale na crypte to zabíja risk management — preto `qty_step`.
        """
        stepped = math.floor(qty / self.qty_step) * self.qty_step
        # floor v plávajúcej desatinnej čiarke vie useknúť o jeden krok nižšie
        stepped = round(stepped, 12)
        return max(self.min_qty, stepped)

    def qty_for_risk(self, risk_amount: float, sl_distance: float) -> float:
        """qty = risk / (SL vzdialenosť v cene × hodnota bodu).

        Ekvivalent Pine riadkov 2010–2016, ale bez ``tickDollarValue``:
        ``slDistTicks * tickDollarValue == sl_distance * point_value``.
        """
        if risk_amount <= 0 or sl_distance <= 0:
            return self.min_qty
        return self.round_qty(risk_amount / (sl_distance * self.point_value))

    def qty_for_risk_pine(
        self, risk_amount: float, sl_distance: float, tick_dollar_value: float
    ) -> float:
        """Doslovná replika Pine výpočtu vrátane jeho chyby — pre golden testy.

        Pine (riadky 2010–2016) zaokrúhľuje na celé kontrakty cez ``int(math.floor(...))``
        a potom to podrží na ``math.max(1, ...)``. Na inštrumente, kde vyjde qty < 1,
        to znamená, že sa ``maxLossDollar`` **ticho neuplatní** a obchoduje sa qty=1.
        Presne to sa dialo na BTCUSD referenčnom grafe, takže bez tejto vetvy by sa
        golden test proti TradingView nedal dosiahnuť.

        Používa sa len keď je ``IBSConfig.legacyPineSizing`` zapnuté.
        """
        if risk_amount <= 0 or sl_distance <= 0 or tick_dollar_value <= 0:
            return 1.0
        sl_dollar_per_contract = (sl_distance / self.tick_size) * tick_dollar_value
        if sl_dollar_per_contract <= 0:
            return 1.0
        return float(max(1, math.floor(risk_amount / sl_dollar_per_contract)))


# --------------------------------------------------------------------------- #
# Presety
# --------------------------------------------------------------------------- #

#: Micro E-mini Nasdaq-100 — tick 0.25 bodu, $0.50/tick ⇒ $2/bod.
#: Toto je inštrument, pre ktorý je pôvodný Pine config vyladený
#: (`tickDollarValue = 0.5` == 0.25 × 2.0).
MNQ = InstrumentSpec(
    symbol="MNQ",
    venue="CME",
    tick_size=0.25,
    point_value=2.0,
    qty_step=1.0,
    min_qty=1.0,
)

#: Referenčný pár zo screenshotov v docs/ — Freqtrade Coinbase NEPODPORUJE,
#: slúži na overenie logiky proti TradingView (viď ARCHITECTURE_port.md §3b).
BTCUSD_COINBASE = InstrumentSpec(
    symbol="BTC-USD",
    venue="coinbase",
    tick_size=0.01,
    point_value=1.0,
    qty_step=0.00000001,
    min_qty=0.00000001,
    quote_currency="USD",
)

#: Exekučný pár — USDⓈ-M perpetual. tick_size/qty_step si adaptér za behu
#: prepíše hodnotami z burzy, tieto sú len fallback.
BTCUSDT_BINANCE = InstrumentSpec(
    symbol="BTC/USDT:USDT",
    venue="binance",
    tick_size=0.1,
    point_value=1.0,
    qty_step=0.001,
    min_qty=0.001,
    quote_currency="USDT",
)

#: Binance ETH/USDT perpetual. Tick je 0,01 - teda **desaťkrát jemnejší než BTC**
#: pri desaťkrát nižšej cene, takže tick ako podiel ceny vyjde podobne. Pozor na to
#: pri prahoch v jednotke `ticks`: rovnaké číslo znamená na ETH iný cenový posun.
ETHUSDT_BINANCE = InstrumentSpec(
    symbol="ETH/USDT:USDT",
    venue="binance",
    tick_size=0.01,
    point_value=1.0,
    qty_step=0.001,
    min_qty=0.001,
    quote_currency="USDT",
)

INSTRUMENTS: dict[str, InstrumentSpec] = {
    "mnq": MNQ,
    "btcusd_coinbase": BTCUSD_COINBASE,
    "btcusdt_binance": BTCUSDT_BINANCE,
    "ethusdt_binance": ETHUSDT_BINANCE,
}
