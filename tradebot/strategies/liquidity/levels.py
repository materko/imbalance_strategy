"""Likvidita na jednom TF: výrazné swing vrcholy (buy-side) a dná (sell-side).

Swing je pivot s `liqPivotLen` barmi z oboch strán (na TF úrovne). **Výrazný** je, keď z neho
cena v tých `liqPivotLen` baroch vpravo odišla aspoň o `liqMinDispAtr` ATR — presne tie body,
z ktorých sa likvidita ručne značí. Úroveň je známa až po potvrdení pivotu (uzavretie
`liqPivotLen`-tého baru vpravo), takže sa nikdy nepozerá dopredu.

Vyšší TF sa skladá z barov grafu (`TFAggregator`, rovnaké pravidlo ako `core/candles.py`).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from tradebot.core.types import Bar

__all__ = ["Level", "SwingFinder"]


@dataclass
class Level:
    """Nevybratá likvidita: vodorovná úroveň od swingu, kým ju cena nezoberie."""

    side: str        #: "buy" (nad vrcholom — stopky shortov) alebo "sell" (pod dnom)
    price: float
    start_ms: int    #: čas swing baru — odtiaľ sa úroveň kreslí
    tf: int          #: TF, na ktorom vznikla (pri zlúčení najvyšší)
    expires_ms: int
    strength: int = 1  #: koľko rovnakých vrcholov/dien je v nej zlúčených
    uid: int = 0

    @property
    def label(self) -> str:
        tf = f"{self.tf // 60}h" if self.tf >= 60 else f"{self.tf}m"
        return f"{'BSL' if self.side == 'buy' else 'SSL'} {tf}" + (f" ×{self.strength}" if self.strength > 1 else "")


class SwingFinder:
    """Výrazné swingy jedného TF; `push(bar)` vráti nové úrovne potvrdené týmto barom."""

    def __init__(self, tf_minutes: int, pivot_len: int, min_disp_atr: float, atr_len: int,
                 max_age_ms: int) -> None:
        self.tf = int(tf_minutes)
        self.tf_ms = self.tf * 60_000
        self.n = int(pivot_len)
        self.min_disp = float(min_disp_atr)
        self.atr_len = int(atr_len)
        self.max_age_ms = int(max_age_ms)
        self.bars: deque[Bar] = deque(maxlen=2 * self.n + 2)
        self.atrs: deque[float] = deque(maxlen=2 * self.n + 2)
        self.atr = 0.0
        self._seed: list[float] = []
        self.count = 0

    def _update_atr(self, b: Bar) -> None:
        prev = self.bars[-1] if self.bars else None
        tr = b.high - b.low if prev is None else max(b.high - b.low, abs(b.high - prev.close),
                                                     abs(b.low - prev.close))
        if self.atr > 0:
            self.atr += (tr - self.atr) / self.atr_len
        else:
            self._seed.append(tr)
            if len(self._seed) >= self.atr_len:
                self.atr = sum(self._seed) / len(self._seed)

    def push(self, b: Bar) -> list[Level]:
        self._update_atr(b)
        self.bars.append(b)
        self.atrs.append(self.atr)
        self.count += 1
        n = self.n
        if len(self.bars) < 2 * n + 1:
            return []
        c = self.bars[-n - 1]
        a = self.atrs[-n - 1]
        if a <= 0:
            return []
        left = [self.bars[-n - 1 - k] for k in range(1, n + 1)]
        right = [self.bars[-k] for k in range(1, n + 1)]
        conf_ms = b.time + self.tf_ms
        out: list[Level] = []
        if all(c.high > x.high for x in left) and all(c.high >= x.high for x in right):
            if c.high - min(x.low for x in right) >= self.min_disp * a:
                out.append(Level("buy", c.high, c.time, self.tf, conf_ms + self.max_age_ms))
        if all(c.low < x.low for x in left) and all(c.low <= x.low for x in right):
            if max(x.high for x in right) - c.low >= self.min_disp * a:
                out.append(Level("sell", c.low, c.time, self.tf, conf_ms + self.max_age_ms))
        return out
