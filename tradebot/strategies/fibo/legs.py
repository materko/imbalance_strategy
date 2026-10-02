"""Swingy a nohy pre Fibonacci ako samostatný stavebný blok.

Stratégia, ktorá fibo používa len ako filter (konfluenciu) k vlastnej úrovni, si nohu nemusí
hľadať sama: `SwingLegs` dostáva bary grafu, skladá z nich TF swingov a drží poslednú rastúcu
a poslednú klesajúcu nohu. Noha = od posledného swingu opačnej strany po práve potvrdený swing
(pivot so `swing_len` barmi z oboch strán), aspoň `leg_min_atr` ATR dlhá. 0 % = koniec nohy,
100 % = jej začiatok. Kým cena nohu predlžuje, koniec sa posúva; prerazením 100 % noha zaniká.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from tradebot.core.types import Bar, Direction

from ..jss.engine import StructAggregator

__all__ = ["Leg", "SwingLegs"]


@dataclass
class Leg:
    uid: int
    direction: Direction
    start: float     #: 100 %
    end: float       #: 0 %
    start_ms: int
    end_ms: int

    @property
    def size(self) -> float:
        return abs(self.end - self.start)

    def level(self, frac: float) -> float:
        """Cena úrovne návratu `frac` (0 = koniec nohy, 1 = začiatok); záporné = extenzia."""
        return self.end - frac * (self.end - self.start)

    def retrace(self, price: float) -> float:
        """Kde na nohe cena leží, ako podiel návratu (0 = koniec, 1 = začiatok)."""
        return (self.end - price) / (self.end - self.start) if self.end != self.start else 0.0


class SwingLegs:
    """Volaj ``on_bar`` raz na každý uzavretý bar grafu; ``legs`` sú nohy známe po tomto bare."""

    def __init__(self, swing_tf: int, chart_tf: int, swing_len: int, atr_len: int, leg_min_atr: float) -> None:
        chart_tf = max(1, int(chart_tf))
        tf = int(swing_tf)
        if tf < chart_tf or tf % chart_tf:
            tf = -(-max(tf, chart_tf) // chart_tf) * chart_tf
        self.tf = tf
        self.n = int(swing_len)
        self.atr_len = int(atr_len)
        self.leg_min_atr = float(leg_min_atr)
        self.agg = StructAggregator(tf, chart_tf)
        self.bars: deque[Bar] = deque(maxlen=2 * self.n + 4)
        self.idx = -1
        self.atr = 0.0
        self._atr_seed: list[float] = []
        self.ph: tuple[float, int, int] | None = None    #: posledný swing vrchol (cena, index, čas)
        self.pl: tuple[float, int, int] | None = None
        self.legs: dict[Direction, Leg] = {}
        self._uid = 0
        self._seeding = False

    @property
    def seed_bars(self) -> int:
        return 2 * self.n + self.atr_len + 60

    def seed(self, bars, partial: Bar | None) -> None:
        self._seeding = True
        for b in bars:
            self._on_swing_bar(b)
        self._seeding = False
        self.agg.prime(partial)

    def on_bar(self, bar: Bar) -> None:
        for d in list(self.legs):
            leg = self.legs[d]
            up = d is Direction.LONG
            if (bar.low < leg.start) if up else (bar.high > leg.start):
                del self.legs[d]                         # 100 % prerazené — už to nie je návrat
            elif (bar.high > leg.end) if up else (bar.low < leg.end):
                leg.end, leg.end_ms = (bar.high if up else bar.low), bar.time    # noha pokračuje
        for sb in self.agg.push(bar):
            self._on_swing_bar(sb)

    def _on_swing_bar(self, b: Bar) -> None:
        prev = self.bars[-1] if self.bars else None
        tr = b.high - b.low if prev is None else max(b.high - b.low, abs(b.high - prev.close), abs(b.low - prev.close))
        if self.atr > 0:
            self.atr += (tr - self.atr) / self.atr_len
        else:
            self._atr_seed.append(tr)
            if len(self._atr_seed) >= self.atr_len:
                self.atr = sum(self._atr_seed) / len(self._atr_seed)
        self.bars.append(b)
        self.idx += 1
        n = self.n
        if len(self.bars) < 2 * n + 1:
            return
        c = self.bars[-n - 1]
        right = [self.bars[-k] for k in range(1, n + 1)]
        side = [self.bars[-n - 1 - k] for k in range(1, n + 1)] + right
        if all(c.high > x.high for x in side):
            self.ph = (c.high, self.idx - n, c.time)
            self._leg(Direction.LONG, right)
        if all(c.low < x.low for x in side):
            self.pl = (c.low, self.idx - n, c.time)
            self._leg(Direction.SHORT, right)

    def _leg(self, d: Direction, right: list[Bar]) -> None:
        up = d is Direction.LONG
        end, start = (self.ph, self.pl) if up else (self.pl, self.ph)
        if self._seeding or end is None or start is None or start[1] >= end[1] or self.atr <= 0:
            return
        size = end[0] - start[0] if up else start[0] - end[0]
        if size <= 0 or size < self.leg_min_atr * self.atr:
            return
        ext = min(x.low for x in right) if up else max(x.high for x in right)
        if (ext <= start[0]) if up else (ext >= start[0]):
            return       # ešte pred potvrdením swingu cena prerazila 100 %
        self._uid += 1
        self.legs[d] = Leg(self._uid, d, start[0], end[0], start[2], end[2])
