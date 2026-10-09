"""Priemerný ATR za N seáns — spoločný pre Volt Break a Overnight Bias ORB (oba Pine skripty ho majú rovnaký).

Dva zdroje, ako Pine vstup „Zdroj ATR":

* ``SessionAvgAtr`` — ATR zo seáns polnoc–16:00 CT (Matteo: „ATR of the past 15 sessions from midnight
  to the end of the trading day"). Seansa sa uzavrie na prvom bare o 16:00 CT alebo neskôr; true range
  seansy proti close predošlej seansy, ATR je prvých `atr_len` seáns priemer a potom Wilderova rekurzia,
  hodnota = priemer posledných `avg_len` ATR. Riadok po riadku Pine (sessBeg / sessDone).
* ``DailyAvgAtr`` — Pine `request.security("D", ta.sma(ta.atr(atrLen), avgLen)[1], lookahead_on)`:
  denné sviečky burzy (CME obchodný deň začína o 17:00 CT predošlého dňa), hodnota z poslednej
  uzavretej dennej sviečky.

Obe dostávajú bar grafu a jeho minútu v pásme Chicaga; `value` je `None`, kým nie je dosť seáns.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from tradebot.core.types import Bar

__all__ = ["SessionAvgAtr", "DailyAvgAtr", "SESSION_END_MIN"]

#: koniec seansy pre ATR — 16:00 CT
SESSION_END_MIN = 16 * 60


class SessionAvgAtr:
    def __init__(self, atr_len: int, avg_len: int) -> None:
        self.atr_len = max(1, int(atr_len))
        self.avg_len = max(1, int(avg_len))
        self._prev_in = False
        self.s_h: float | None = None
        self.s_l: float | None = None
        self.s_c: float | None = None
        self.prev_c: float | None = None
        self.atr: float | None = None
        self.n = 0
        self.hist: deque[float] = deque(maxlen=self.avg_len)

    @property
    def value(self) -> float | None:
        return sum(self.hist) / len(self.hist) if len(self.hist) >= self.avg_len else None

    def push(self, bar: Bar, bar_min: int) -> float | None:
        in_sess = bar_min < SESSION_END_MIN
        beg = in_sess and not self._prev_in
        done = not in_sess and self._prev_in
        if done and self.s_h is not None:
            tr = (self.s_h - self.s_l if self.prev_c is None
                  else max(self.s_h, self.prev_c) - min(self.s_l, self.prev_c))
            self.n += 1
            if self.atr is None:
                self.atr = tr
            elif self.n <= self.atr_len:
                self.atr += (tr - self.atr) / self.n
            else:
                self.atr = (self.atr * (self.atr_len - 1) + tr) / self.atr_len
            self.hist.append(self.atr)
            self.prev_c = self.s_c
        if beg:
            self.s_h, self.s_l = bar.high, bar.low
        elif in_sess and self.s_h is not None:
            self.s_h = max(self.s_h, bar.high)
            self.s_l = min(self.s_l, bar.low)
        if in_sess:
            self.s_c = bar.close
        self._prev_in = in_sess
        return self.value


class DailyAvgAtr:
    #: CME obchodný deň začína o 17:00 CT predošlého dňa -> posun o 7 h dá dátum obchodného dňa
    DAY_SHIFT = timedelta(hours=7)

    def __init__(self, atr_len: int, avg_len: int) -> None:
        self.atr_len = max(1, int(atr_len))
        self.avg_len = max(1, int(avg_len))
        self._day = None
        self._ohlc: list[float] | None = None   # high, low, close
        self._prev_close: float | None = None
        self._seed: list[float] = []
        self.atr: float | None = None
        self.hist: deque[float] = deque(maxlen=self.avg_len)
        self.value: float | None = None

    def push(self, bar: Bar, local: datetime) -> float | None:
        day = (local + self.DAY_SHIFT).date()
        if day != self._day:
            if self._ohlc is not None:
                self._close_day()
            self._day, self._ohlc = day, [bar.high, bar.low, bar.close]
        else:
            o = self._ohlc
            o[0], o[1], o[2] = max(o[0], bar.high), min(o[1], bar.low), bar.close
        return self.value

    def _close_day(self) -> None:
        h, lo, c = self._ohlc
        tr = h - lo if self._prev_close is None else max(h, self._prev_close) - min(lo, self._prev_close)
        self._prev_close = c
        if self.atr is None:              # Pine ta.rma: rozbeh z SMA prvých n hodnôt
            self._seed.append(tr)
            if len(self._seed) == self.atr_len:
                self.atr = sum(self._seed) / self.atr_len
        else:
            self.atr += (tr - self.atr) / self.atr_len
        if self.atr is not None:
            self.hist.append(self.atr)
            if len(self.hist) >= self.avg_len:
                self.value = sum(self.hist) / self.avg_len
