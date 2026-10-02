"""Seansový VWAP bar po bare — priemerná cena vážená objemom od otvorenia seansy.

VWAP je cena, za ktorú sa od kotvy (otvorenie seansy) zobchodovalo najviac peňazí:
``Σ(typická cena × objem) / Σ objem``, typická cena = ``(high + low + close) / 3``
(Pine ``ta.vwap`` a TradingView VWAP so zdrojom hlc3). Každá seansa začína od nuly.

Engine TradeBotu dostáva bary po jednom, preto má indikátor stav a metódu ``push`` —
rovnako ako `tradebot.core.ma`. Je v jadre, lebo ho môže použiť ktorákoľvek stratégia;
dve implementácie by dali dve rôzne čísla z tých istých dát.

Dve voľby, ktoré menia hodnotu:

* **Kotva a pásmo.** Seansa sa zadáva v minútach od polnoci v pásme (štandardne New York
  9:30–16:00, teda RTH cash seansa). Pásmo rieši letný čas samo. Bary mimo seansy sa do
  VWAP nepočítajú a pred prvým barom seansy je hodnota ``None``. Seansa cez polnoc
  (Globex 18:00–17:00) sa zadá ako ``start > end`` a patrí k dňu, v ktorom končí.
* **Perióda.** ``period_minutes=None`` počíta z barov grafu. ``period_minutes=15`` najprv
  zloží bary grafu do 15-minútových sviečok (od kotvy) a VWAP počíta z nich — hodnota sa
  zmení len pri zatvorení 15m sviečky a medzi tým drží poslednú uzavretú. Tak ho vidí
  obchodník, ktorý má na 5m grafe VWAP z 15m grafu; rozpracovaná sviečka sa nepočíta,
  takže nič nerepaintuje.

Objem musí byť skutočný objem burzy (CME futures z Databenta, krypto burzy). Na CFD
z Dukascopy je v stĺpci ``volume`` len aktivita tickov u brokera a VWAP z neho je odhad.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from .types import Bar

__all__ = ["SessionVwap", "session_vwap"]


class SessionVwap:
    """Seansový VWAP. Volaj ``push`` presne raz na každý uzavretý bar grafu.

    ``value``   posledná publikovaná hodnota (``None`` pred prvým barom seansy)
    ``updated`` či sa hodnota na poslednom bare zmenila (pri periode len na jej zatvorení)
    ``history`` posledných ``keep`` publikovaných hodnôt dnešnej seansy, najnovšia posledná
    ``live``    posledný bar bol v seanse — mimo nej ``value`` ostáva zamrznutá na konci
                predošlej seansy a pre rozhodovanie je to včerajší VWAP, nie dnešný
    """

    def __init__(self, chart_tf_minutes: int, *, start_minutes: int = 9 * 60 + 30,
                 end_minutes: int = 16 * 60, tz: str = "America/New_York",
                 period_minutes: int | None = None, keep: int = 64) -> None:
        self.tf = max(1, int(chart_tf_minutes))
        self.start = int(start_minutes)
        self.end = int(end_minutes)
        self.zone = ZoneInfo(tz)
        self.period = int(period_minutes) if period_minutes else None
        self.value: float | None = None
        self.updated = False
        self.live = False
        self.history: deque[float] = deque(maxlen=max(2, int(keep)))
        self.day: tuple[int, int, int] | None = None
        self._pv = 0.0
        self._vol = 0.0
        # rozpracovaná perióda: (index, high, low, close, objem)
        self._bucket: list | None = None

    # ------------------------------------------------------------------ #

    def _session_minute(self, local: datetime) -> tuple[tuple[int, int, int], int] | None:
        """Deň seansy a minúta od kotvy, alebo ``None`` mimo seansy."""
        m = local.hour * 60 + local.minute
        day = (local.year, local.month, local.day)
        if self.start < self.end:
            return (day, m - self.start) if self.start <= m < self.end else None
        # seansa cez polnoc: večerná časť patrí k nasledujúcemu dňu
        if m >= self.start:
            nxt = datetime.fromordinal(local.date().toordinal() + 1)
            return (nxt.year, nxt.month, nxt.day), m - self.start
        if m < self.end:
            return day, m + 1440 - self.start
        return None

    def _reset(self, day: tuple[int, int, int]) -> None:
        self.day = day
        self.value = None
        self.history.clear()
        self._pv = self._vol = 0.0
        self._bucket = None

    def _add(self, high: float, low: float, close: float, volume: float) -> None:
        if volume <= 0:
            return
        self._pv += (high + low + close) / 3.0 * volume
        self._vol += volume
        self.value = self._pv / self._vol
        self.history.append(self.value)
        self.updated = True

    def push(self, bar: Bar) -> float | None:
        self.updated = False
        local = datetime.fromtimestamp(bar.time / 1000, tz=self.zone)
        pos = self._session_minute(local)
        self.live = pos is not None
        if pos is None:
            return self.value
        day, minute = pos
        if day != self.day:
            self._reset(day)

        if self.period is None:
            self._add(bar.high, bar.low, bar.close, bar.volume)
            return self.value

        idx = minute // self.period
        b = self._bucket
        if b is not None and b[0] != idx:  # diera v dátach: stará perióda sa už nedoplní
            self._add(b[1], b[2], b[3], b[4])
            b = None
        if b is None:
            b = [idx, bar.high, bar.low, bar.close, bar.volume]
        else:
            b[1] = max(b[1], bar.high)
            b[2] = min(b[2], bar.low)
            b[3] = bar.close
            b[4] += bar.volume
        self._bucket = b
        # perióda sa zatvára na bare, za ktorým by ďalší bar začal v novej perióde alebo po seanse
        span = (self.end - self.start) % 1440 or 1440
        nxt = minute + self.tf
        if nxt // self.period != idx or nxt >= span:
            self._add(b[1], b[2], b[3], b[4])
            self._bucket = None
        return self.value

    def change(self, bars_back: int) -> float | None:
        """O koľko sa VWAP zmenil za posledných ``bars_back`` publikovaných hodnôt."""
        n = int(bars_back)
        if n < 1 or len(self.history) <= n:
            return None
        return self.history[-1] - self.history[-1 - n]


def session_vwap(df, *, start_minutes: int = 9 * 60 + 30, end_minutes: int = 16 * 60,
                 tz: str = "America/New_York", period_minutes: int | None = None,
                 chart_tf_minutes: int | None = None):
    """VWAP pre celý DataFrame (stĺpce ``date`` v UTC, ``high``, ``low``, ``close``, ``volume``).

    Na graf a na kontrolu voči TradingView; počíta sa tým istým `SessionVwap`, takže dá
    presne to, čo vidí stratégia. Vráti `pandas.Series` s indexom DataFrame (``NaN`` mimo
    seansy a pred prvou uzavretou periódou).
    """
    import pandas as pd

    ts = pd.to_datetime(df["date"], utc=True)
    if chart_tf_minutes is None:
        step = ts.diff().dropna()
        chart_tf_minutes = max(1, int(step.min().total_seconds() // 60)) if len(step) else 1
    ind = SessionVwap(chart_tf_minutes, start_minutes=start_minutes, end_minutes=end_minutes,
                      tz=tz, period_minutes=period_minutes)
    ms = ts.dt.as_unit("ms").astype("int64")
    out = []
    for t, h, lo, c, v in zip(ms, df["high"], df["low"], df["close"], df["volume"]):
        val = ind.push(Bar(int(t), 0.0, float(h), float(lo), float(c), float(v)))
        in_session = ind._session_minute(datetime.fromtimestamp(t / 1000, tz=ind.zone)) is not None
        out.append(val if in_session else None)
    return pd.Series(out, index=df.index, dtype="float64", name="vwap")
