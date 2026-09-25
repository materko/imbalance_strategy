"""Okno detekčného TF pre IBSZones — synchronizované s dátami, nie s barom grafu.

Rozdiel oproti `tradebot/strategies/ibs/htf.py` je jediný riadok logiky a je to celý
dôvod, prečo táto stratégia existuje samostatne.

IBS (a Pine predloha) spúšťa detekciu podľa toho, či aktuálny bar GRAFU už patrí do
novej periódy detekčného TF — v Pine je to ``ta.change(time(zoneDetectionTF))``, tu bolo
``ts_ms // htf_ms``. Lenže okno barov, z ktorého sa pattern číta, počíta
`htf_window_opens()` z času UZAVRETIA baru grafu, lebo presne tak sa správa
``request.security(..., lookahead_off)``. Tieto dva časy sa pri neprekrývajúcich sa
mriežkach rozchádzajú a posun závisí od TF grafu::

    1m graf, bar 9:05 -> perióda už hlási 9:05, ale okno končí barom 8:55
    4m graf, bar 9:08 -> perióda hlási 9:05  a okno už končí barom 9:00

Na každom TF grafu sa teda vyhodnocoval iný pattern a zóny vychádzali inde — najmä na
krajoch okna seansy, kde posunutý pattern do okna už nespadol.

Tu sa spúšťa podľa ``opens[0]``, teda podľa najnovšieho baru toho istého okna, aké
engine dostane. Gate a dáta sú tým pádom vždy z tej istej sviečky detekčného TF a zóny
vyjdú rovnako bez ohľadu na TF grafu.

**Preto to nie je oprava v `ibs`:** `ibs` má golden testy bar po bare proti TradingView
(`tester/tests/test_golden_tv_binance.py`) a TradingView sa správa podľa Pine predlohy.
Oprava v `ibs` by tie testy rozbila — a prestali by merať to, na čo sú.
"""

from __future__ import annotations

from ..ibs.htf import HTFFeeder, HTFWindow, htf_window_opens

__all__ = ["ZoneSyncHTFFeeder", "HTFWindow", "htf_window_opens"]


class ZoneSyncHTFFeeder(HTFFeeder):
    """`HTFFeeder`, ktorý novú periódu pozná z okna dát, nie z času baru grafu."""

    def __init__(self, cfg, chart_tf_minutes: int, *, keep: int | None = None) -> None:
        super().__init__(cfg, chart_tf_minutes, keep=keep)
        #: otvárací čas najnovšieho HTF baru v okne (Pine ``t5_0``), z ktorého sa gate púšťa
        self._prev_newest: int | None = None

    def window_for(self, ts_ms: int) -> HTFWindow | None:
        opens = htf_window_opens(ts_ms, self.step_ms, self.htf_ms)
        newest = opens[0]
        # Prvé volanie periódu nespúšťa — rovnako ako v IBS (nemáme s čím porovnať).
        is_new_period = self._prev_newest is not None and newest != self._prev_newest
        self._prev_newest = newest
        if not is_new_period:
            return None
        if any(o not in self.bars for o in opens):
            return None
        return HTFWindow(tuple(self.bars[o] for o in opens), self.vol_sma.get(opens[0], 0.0))
