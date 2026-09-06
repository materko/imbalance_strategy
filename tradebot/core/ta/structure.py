"""Market Structure — swingy HH/HL/LH/LL a prerazenia BOS/CHoCH.

Replika Pine riadkov 706–820.

Swing sa potvrdí cez `ta.pivothigh`/`ta.pivotlow`, čo je nutne oneskorené
o `structureSwingLen` barov — skôr sa nedá vedieť, že ide o lokálny vrchol.
Keď potom cena zavrie nad posledným potvrdeným swing high:

* ak bola štruktúra predtým bearish → **CHoCH** (zmena charakteru)
* ak už bola bullish → **BOS** (pokračovanie trendu)

Zrkadlovo pre swing low.

`HH/HL/LH/LL` je nezávislé značenie: priradí sa hneď pri potvrdení swingu, kým
BOS/CHoCH vzniká až keď cena úroveň prerazí.

Modul počíta aj `market_bias`, ktorý Pine používa vo filtri `useStructureFilter`.
V referenčných profiloch je ten filter vypnutý, takže na obchody zatiaľ nemá vplyv.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..drawing import (
    PAL,
    DrawCommand,
    DrawKind,
    DrawLabel,
    DrawLine,
    LabelStyle,
    LineStyle,
    with_alpha,
)
from ..history import BarHistory
from ..types import Bar, InstrumentSpec

__all__ = ["MarketStructure", "Swing", "pivot"]


@dataclass(frozen=True, slots=True)
class Swing:
    """Potvrdený swing bod."""

    ts_ms: int
    bar_index: int
    price: float
    is_high: bool


def pivot(
    history: BarHistory, length: int, *, high: bool, source: str = "hl"
) -> float | None:
    """Pine ``ta.pivothigh(length, length)`` / ``ta.pivotlow``.

    Stred okna je bar vzdialený `length` dozadu.

    **Porovnanie je asymetrické a je to zámer.** Pine na ľavej strane pripúšťa
    ZHODU, vpravo vyžaduje prísne nižšie high (resp. vyššie low). S obojstranne
    prísnym porovnaním sa zahadzujú pivoty, ktoré TradingView nájde — na
    Elliott zigzagu to znamenalo 32 z 41 bodov namiesto 41 z 41
    (docs/GOLDEN_binance_2026-08-24.md).

    Pozor na indexovanie: `history[0]` je NAJNOVŠÍ bar, takže index menší než
    `length` je vpravo od pivota v čase, nie vľavo.

    `source="hl"` berie high/low (Market Structure), `source="close"` berie close
    (S/R aj likvidita) — tam má úroveň vzniknúť len tam, kde sa cena naozaj
    zavrela na lokálnom extréme, nie kde ju len prepichol knôt.
    """
    need = 2 * length + 1
    if length <= 0 or len(history) < need:
        return None

    def val(b):
        if source == "close":
            return b.close
        return b.high if high else b.low

    value = val(history[length])
    for i in range(need):
        if i == length:
            continue
        other = val(history[i])
        # i < length = novšie bary = vpravo od pivota -> prísne; staršie -> zhoda OK
        strict = i < length
        if high:
            if (other >= value) if strict else (other > value):
                return None
        elif (other <= value) if strict else (other < value):
            return None
    return value


class MarketStructure:
    """Stav štruktúry medzi barmi. Volaj `on_bar` raz na každý uzavretý bar."""

    __slots__ = (
        "cfg",
        "inst",
        "bias",
        "_swing_high",
        "_swing_low",
        "_swing_high_bar",
        "_swing_low_bar",
        "_swing_high_ts",
        "_swing_low_ts",
        "_last_high",
        "_last_low",
        "_seq",
    )

    def __init__(self, cfg, inst: InstrumentSpec) -> None:
        self.cfg = cfg
        self.inst = inst
        #: Pine `marketBias`: +1 bullish, -1 bearish, 0 neurčené.
        self.bias = 0
        # posledný potvrdený swing, ktorý ešte nebol prerazený
        self._swing_high: float | None = None
        self._swing_low: float | None = None
        self._swing_high_bar: int | None = None
        self._swing_low_bar: int | None = None
        self._swing_high_ts: int | None = None
        self._swing_low_ts: int | None = None
        # posledný potvrdený swing vôbec — na porovnanie HH vs LH
        self._last_high: float | None = None
        self._last_low: float | None = None
        self._seq = 0

    def _uid(self) -> int:
        self._seq += 1
        return self._seq

    def on_bar(self, bar: Bar, history: BarHistory) -> list[DrawCommand]:
        cfg = self.cfg
        out: list[DrawCommand] = []
        length = cfg.structureSwingLen
        tick = self.inst.tick_size

        # ---- potvrdenie swingov + HH/HL/LH/LL --------------------------- #
        piv_hi = pivot(history, length, high=True)
        if piv_hi is not None:
            pivot_bar = history[length]
            if cfg.showMarketStructure and self._last_high is not None:
                is_hh = piv_hi > self._last_high
                out.append(
                    DrawLabel(
                        kind=DrawKind.SWING,
                        x_ms=pivot_bar.time,
                        y=piv_hi + tick * 25,
                        text="HH" if is_hh else "LH",
                        color=with_alpha(PAL.STRONG.value if is_hh else PAL.LONG.value, 25),
                        style=LabelStyle.NONE,
                        above=True,
                        obj_id=f"swing.h.{pivot_bar.time}",
                    )
                )
            self._last_high = piv_hi
            self._swing_high = piv_hi
            self._swing_high_bar = history.index_of(length)
            self._swing_high_ts = pivot_bar.time

        piv_lo = pivot(history, length, high=False)
        if piv_lo is not None:
            pivot_bar = history[length]
            if cfg.showMarketStructure and self._last_low is not None:
                is_hl = piv_lo > self._last_low
                out.append(
                    DrawLabel(
                        kind=DrawKind.SWING,
                        x_ms=pivot_bar.time,
                        y=piv_lo - tick * 25,
                        text="HL" if is_hl else "LL",
                        color=with_alpha(PAL.STRONG.value if is_hl else PAL.LONG.value, 25),
                        style=LabelStyle.NONE,
                        above=False,
                        obj_id=f"swing.l.{pivot_bar.time}",
                    )
                )
            self._last_low = piv_lo
            self._swing_low = piv_lo
            self._swing_low_bar = history.index_of(length)
            self._swing_low_ts = pivot_bar.time

        # ---- prerazenie: BOS / CHoCH ------------------------------------ #
        if self._swing_high is not None and bar.close > self._swing_high:
            out += self._break(bar, self._swing_high, self._swing_high_ts, upward=True)
            self.bias = 1
            self._swing_high = None

        if self._swing_low is not None and bar.close < self._swing_low:
            out += self._break(bar, self._swing_low, self._swing_low_ts, upward=False)
            self.bias = -1
            self._swing_low = None

        return out

    def _break(
        self, bar: Bar, level: float, from_ts: int | None, *, upward: bool
    ) -> list[DrawCommand]:
        """Čiara od vzniku swingu po bar prerazenia + štítok v jej strede.

        Čiara je vždy tlmená slate; farba ostáva len na nápise (BOS zelená/červená,
        CHoCH jantárová). BOS má väčšiu vizuálnu váhu — hrubšiu čiaru.
        Štítok je mierne NAD čiarou, aby sa nebil s likviditným „X", ktorý je pod ňou.
        """
        if not self.cfg.showMarketStructure or from_ts is None:
            return []
        is_choch = self.bias == (-1 if upward else 1)
        text = "CHoCH" if is_choch else "BOS"
        color = PAL.AMBER.value if is_choch else (PAL.STRONG.value if upward else PAL.LONG.value)
        uid = self._uid()
        return [
            DrawLine(
                kind=DrawKind.STRUCTURE,
                x1_ms=from_ts,
                y1=level,
                x2_ms=bar.time,
                y2=level,
                color=with_alpha(PAL.SLATE.value, 25),
                style=LineStyle.SOLID,
                width=1 if is_choch else 2,
                obj_id=f"struct.{uid}.line",
                text=text,
            ),
            DrawLabel(
                kind=DrawKind.STRUCTURE,
                x_ms=(from_ts + bar.time) // 2,
                y=level + self.inst.tick_size * 15,
                text=text,
                color=color,
                style=LabelStyle.NONE,
                above=True,
                obj_id=f"struct.{uid}.label",
            ),
        ]
