"""Likvidita (sweep / stop hunt) — replika Pine riadkov 1135–1252.

Sweep je situácia, keď cena krátko prepichne swing high/low (tým „vyberie" stopy
nahromadené za úrovňou), ale hneď sa **potvrdene** zatvorí späť na pôvodnú
stranu. Na rozdiel od BOS, ktorý sa udrží, je to signál možného obratu.

Sledujú sa len „silné" pivoty — musia byť najvyšším/najnižším bodom za posledných
`liqStrengthLen` barov, inak ide o bezvýznamný lokálny zub.

Postupnosť: pivot → prepichnutie o aspoň `liqSweepMinWick` → návrat zavretím späť
do `liqSweepConfirmBars` barov. Ak sa návrat nestihne, bol to reálny breakout
a úroveň sa zahodí.

Modul vracia aj zóny na obchodovanie (`enableLqTrading`); sweep je z definície
fade signál, takže obchod ide vždy **proti** nemu.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..drawing import PAL, DrawCommand, DrawKind, DrawLabel, DrawLine, LabelStyle, LineStyle, with_alpha
from ..history import BarHistory
from ..types import Bar, Direction, InstrumentSpec
from .structure import pivot

__all__ = ["LiquiditySweep", "SweepZone"]


@dataclass(frozen=True, slots=True)
class SweepZone:
    """Obchodovateľná zóna, ktorá vznikla z potvrdeného sweepu."""

    direction: Direction
    top: float
    bot: float


class LiquiditySweep:
    """Stav sledovania oboch strán. Volaj `on_bar` raz na každý uzavretý bar."""

    __slots__ = ("cfg", "inst", "_hi", "_lo", "_seq")

    def __init__(self, cfg, inst: InstrumentSpec) -> None:
        self.cfg = cfg
        self.inst = inst
        # (úroveň, ts vzniku, prepichnuté?, ts prepichnutia, bar_index prepichnutia, extrém)
        self._hi: dict | None = None
        self._lo: dict | None = None
        self._seq = 0

    def on_bar(
        self, bar: Bar, history: BarHistory
    ) -> tuple[list[DrawCommand], list[SweepZone]]:
        cfg = self.cfg
        out: list[DrawCommand] = []
        zones: list[SweepZone] = []
        length = cfg.liqSweepLen

        # ---- nové "silné" pivoty --------------------------------------- #
        piv_hi = pivot(history, length, high=True)
        if piv_hi is not None and piv_hi >= self._extreme(history, high=True):
            self._hi = {"level": piv_hi, "ts": history[length].time, "pierced": False}
        piv_lo = pivot(history, length, high=False)
        if piv_lo is not None and piv_lo <= self._extreme(history, high=False):
            self._lo = {"level": piv_lo, "ts": history[length].time, "pierced": False}

        min_wick = cfg.liqSweepMinWick.resolve(self.inst, price=bar.close)

        # ---- sell-side: nad swing high ---------------------------------- #
        if self._hi is not None:
            st = self._hi
            if not st["pierced"]:
                if bar.high - st["level"] >= min_wick:
                    st.update(pierced=True, pierce_ts=bar.time, pierce_idx=history.bar_index,
                              extreme=bar.high)
            else:
                st["extreme"] = max(st["extreme"], bar.high)
                since = history.bar_index - st["pierce_idx"]
                if bar.close < st["level"] and since <= cfg.liqSweepConfirmBars:
                    out += self._draw(st, "X ↓")
                    if cfg.enableLqTrading:
                        top, bot = self._span(st["extreme"], st["level"])
                        zones.append(SweepZone(Direction.SHORT, top, bot))
                    self._hi = None
                elif since > cfg.liqSweepConfirmBars:
                    self._hi = None  # návrat neprišiel → bol to breakout, nie sweep

        # ---- buy-side: pod swing low ------------------------------------ #
        if self._lo is not None:
            st = self._lo
            if not st["pierced"]:
                if st["level"] - bar.low >= min_wick:
                    st.update(pierced=True, pierce_ts=bar.time, pierce_idx=history.bar_index,
                              extreme=bar.low)
            else:
                st["extreme"] = min(st["extreme"], bar.low)
                since = history.bar_index - st["pierce_idx"]
                if bar.close > st["level"] and since <= cfg.liqSweepConfirmBars:
                    out += self._draw(st, "X ↑")
                    if cfg.enableLqTrading:
                        top, bot = self._span(st["level"], st["extreme"])
                        zones.append(SweepZone(Direction.LONG, top, bot))
                    self._lo = None
                elif since > cfg.liqSweepConfirmBars:
                    self._lo = None

        return out, zones

    # ------------------------------------------------------------------ #

    def _extreme(self, history: BarHistory, *, high: bool) -> float:
        """Pine ``ta.highest(high, liqStrengthLen)`` / ``ta.lowest(low, …)``."""
        n = min(self.cfg.liqStrengthLen, len(history))
        vals = [history[i].high if high else history[i].low for i in range(n)]
        return max(vals) if high else min(vals)

    def _span(self, top: float, bot: float) -> tuple[float, float]:
        """Zóna musí mať nenulovú výšku, aj keď prepichnutie bolo presné."""
        if top == bot:
            return top + self.inst.tick_size * 2, bot - self.inst.tick_size * 2
        return top, bot

    def _draw(self, st: dict, text: str) -> list[DrawCommand]:
        """Bodkovaná čiara od vzniku swingu po bar prepichnutia + „X" v jej strede.

        „X" je vždy mierne POD čiarou — BOS/CHoCH je vždy nad svojou, takže keď sa
        stretnú na tom istom mieste, nápisy sa neprekryjú.
        """
        if not self.cfg.showLiqSweep:
            return []
        self._seq += 1
        uid = self._seq
        level, x1, x2 = st["level"], st["ts"], st["pierce_ts"]
        return [
            DrawLine(
                kind=DrawKind.LIQ_SWEEP,
                x1_ms=x1,
                y1=level,
                x2_ms=x2,
                y2=level,
                color=with_alpha(PAL.LONG.value, 20),
                style=LineStyle.DOTTED,
                width=1,
                obj_id=f"liq.{uid}.line",
                text=text,
            ),
            DrawLabel(
                kind=DrawKind.LIQ_SWEEP,
                x_ms=(x1 + x2) // 2,
                y=level - self.inst.tick_size * 15,
                text=text,
                color=PAL.LONG.value,
                style=LabelStyle.NONE,
                above=False,
                obj_id=f"liq.{uid}.label",
            ),
        ]
