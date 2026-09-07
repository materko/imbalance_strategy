"""Informatívny TF (Data2) zo súboru namiesto z grafu.

MultiCharts x Python beta odmieta študii `BarsOfData(2)` (väzba série padá v
`PriceSeriesImpl.ReBind`), hoci graf druhú sériu má. Kým to beta neopraví, dá sa
detekčný TF poskladať z **1m Dukascopy CSV** na disku — z toho istého súboru, z ktorého
vznikli dáta v QuoteManageri (`tradebot.tools.dukas_import`) a ktorý číta offline
simulátor (`scan_trades --csv`). Všetky tri cesty tak vidia tie isté 5m bary.

Čisté stdlib: v Pythone, ktorý používa MultiCharts, nemusí byť pandas. Desaťročný
export (6 mil. riadkov) sa spracuje za ~20–40 s pri štarte študie; drží sa len
poskladaný TF, nie 1m bary.
"""

from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path

from ...core import Bar
from ...tools.dukas_import import _parse

__all__ = ["CsvHtfFeed", "aggregate_csv"]


def aggregate_csv(path: str | Path, htf_minutes: int, *, drop_padding: bool = True) -> list[Bar]:
    """1m Dukascopy CSV (`dt,o,h,l,c,vol`, UTC, čas otvorenia) → uzavreté bary `htf_minutes`.

    Bary sú zarovnané na násobky TF od epochy (rovnako ako `htf_window_opens` v jadre
    a `resample(origin="epoch")` v simulátore). Vypchávka (plochý bar s cenou
    predchádzajúceho uzavretia) sa zahadzuje ako všade inde.
    """
    step = htf_minutes * 60_000
    bars: list[Bar] = []
    cur_open: int | None = None
    o = h = l = c = v = 0.0
    prev_close: float | None = None

    def flush() -> None:
        if cur_open is not None:
            bars.append(Bar(time=cur_open, open=o, high=h, low=l, close=c, volume=v))

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            row = _parse(line)
            if row is None:
                continue
            dt, ro, rh, rl, rc, rv = row
            is_padding = ro == rh == rl == rc and prev_close is not None and rc == prev_close
            prev_close = rc
            if drop_padding and is_padding:
                continue
            ts = int(datetime.fromisoformat(dt).replace(tzinfo=timezone.utc).timestamp() * 1000)
            bucket = ts // step * step
            if bucket != cur_open:
                flush()
                cur_open, o, h, l, c, v = bucket, ro, rh, rl, rc, rv
            else:
                h = max(h, rh)
                l = min(l, rl)
                c = rc
                v += rv
    flush()
    return bars


class CsvHtfFeed:
    """Kŕmi `MCRunner.feed_htf` uzavretými HTF barmi zo súboru, bar po bare grafu.

    `feed_until(runner, close_ms)` pošle všetky HTF bary, ktoré sa zavreli najneskôr
    v `close_ms` (čas zatvorenia aktuálneho baru grafu) — presne to, čo by dala Data2
    s offsetom [1]. Nič z budúcnosti sa nepustí.
    """

    def __init__(self, path: str | Path, htf_minutes: int) -> None:
        self.path = Path(path)
        self.htf_minutes = htf_minutes
        self.bars = aggregate_csv(self.path, htf_minutes)
        self._closes = [b.time + htf_minutes * 60_000 for b in self.bars]
        self._pos = 0

    def __len__(self) -> int:
        return len(self.bars)

    def feed_until(self, runner, close_ms: int) -> int:
        """Vráti počet práve nakŕmených barov."""
        end = bisect_right(self._closes, close_ms)
        if end <= self._pos:
            return 0
        for b in self.bars[self._pos:end]:
            runner.feed_htf(b)
        fed = end - self._pos
        self._pos = end
        return fed

    def describe(self) -> str:
        if not self.bars:
            return f"{self.path.name}: 0 barov"
        first = datetime.fromtimestamp(self.bars[0].time / 1000, tz=timezone.utc)
        last = datetime.fromtimestamp(self.bars[-1].time / 1000, tz=timezone.utc)
        return f"{self.path.name}: {len(self.bars)} barov {self.htf_minutes}m, {first:%Y-%m-%d} .. {last:%Y-%m-%d}"
