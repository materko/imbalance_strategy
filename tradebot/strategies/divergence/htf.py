"""Vyšší TF poskladaný z barov grafu — priamo v engine, bez informatívnej série.

Pôvodná stratégia si 1h a 4h ťahala cez `merge_informative_pair`; rámec TradeBotu má
feeder pre **jeden** informatívny TF (IBS: detekčný TF zón, MultiCharts Data2). Táto
stratégia potrebuje dva, a oba sú násobkom grafu, takže sa skladajú tu z uzavretých
barov grafu. Pravidlo skladania je to isté ako v `tradebot/core/candles.py`: bar je
zarovnaný na násobok TF **od epochy** a perióda bez jediného baru grafu neexistuje —
z 15m barov tak vznikne bit po bite ten istý 1h bar ako z 1m.

Kedy je HTF bar k dispozícii: na **prvom bare grafu novej periódy** — presne ako
`merge_informative_pair` (Freqtrade) aj `htf_window_opens` (IBS). Bar 12:00–13:00 sa teda
prvýkrát použije na bare grafu, ktorý sa otvára o 13:00. Nikdy sa nepoužije rozpracovaný
HTF bar, takže engine nikdy nerepaintuje.

Vyžaduje, aby TF grafu delil HTF (15m → 60m áno, 45m → 60m nie); engine to skontroluje
pri štarte.
"""

from __future__ import annotations

from tradebot.core.types import Bar

__all__ = ["TFAggregator"]


class TFAggregator:
    """Uzavreté bary vyššieho TF z barov grafu; `push` vráti bar, ktorý sa práve uzavrel."""

    __slots__ = ("minutes", "ms", "_open_ts", "_o", "_h", "_l", "_c", "_v", "closed_count")

    def __init__(self, minutes: int) -> None:
        self.minutes = int(minutes)
        self.ms = self.minutes * 60_000
        self._open_ts: int | None = None
        self._o = self._h = self._l = self._c = self._v = 0.0
        self.closed_count = 0

    def push(self, bar: Bar) -> Bar | None:
        """Pridá bar grafu; keď ním začína nová perióda, vráti predchádzajúci (uzavretý) HTF bar."""
        period = bar.time // self.ms * self.ms
        closed: Bar | None = None
        if self._open_ts is not None and period != self._open_ts:
            closed = Bar(time=self._open_ts, open=self._o, high=self._h, low=self._l,
                         close=self._c, volume=self._v)
            self.closed_count += 1
            self._open_ts = None
        if self._open_ts is None:
            self._open_ts = period
            self._o, self._h, self._l, self._c, self._v = bar.open, bar.high, bar.low, bar.close, bar.volume
        else:
            self._h = max(self._h, bar.high)
            self._l = min(self._l, bar.low)
            self._c = bar.close
            self._v += bar.volume
        return closed
