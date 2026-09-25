"""Veľké imbalance (fair value gap) z vyšších TF — 5m, 15m, 30m a 1h.

Vrstva **nič neobchoduje a nič nefiltruje**: len nájde medzery a engine z nich spraví
obyčajné zóny v tej istej knihe, v akej žijú SD zóny. Ďalej ich rieši rovnaký stavový
automat (STATE 0–5), kreslia sa rovnako a platia pre ne rovnaké entry modely — presne
ako pri zónach zo S/R úrovní a z likvidity, ktoré IBS pozná už dnes.

Vyššie TF sa skladajú z barov grafu **rovnakým pravidlom ako `tradebot/core/candles.py`**:
bucket je ``floor(time / tf) * tf`` (zarovnanie od epochy), perióda bez barov sa
nevypchráva. Preto tu nie je `request.security` ani informatívny TF navyše — obom
enginom stačia bary, ktoré už aj tak majú, a vidia to isté.
"""

from __future__ import annotations

from dataclasses import dataclass

from tradebot.core.types import Bar

__all__ = ["FVG_TIMEFRAMES", "FvgHit", "TimeframeAggregator", "FvgDetector"]

#: TF, z ktorých sa čítajú veľké imbalance — pole configu -> minúty.
FVG_TIMEFRAMES: tuple[tuple[str, int], ...] = (
    ("fvgUse5m", 5),
    ("fvgUse15m", 15),
    ("fvgUse30m", 30),
    ("fvgUse60m", 60),
)


@dataclass(frozen=True, slots=True)
class FvgHit:
    """Nájdená medzera medzi 1. a 3. sviečkou trojice na danom TF."""

    top: float
    bot: float
    direction: int  #: +1 = bullish (medzera pod cenou, dopyt), -1 = bearish (ponuka)
    tf_minutes: int

    @property
    def size(self) -> float:
        return self.top - self.bot


class TimeframeAggregator:
    """Skladá bary grafu na vyšší TF a vracia ich, až keď sa sviečka UZAVRELA.

    Rovnaké zarovnanie ako `core/candles.py` (`origin="epoch"`, `label/closed="left"`).
    Prázdna perióda sa nevypchráva plochým barom — jednoducho nevznikne.
    """

    def __init__(self, minutes: int) -> None:
        self.tf_ms = int(minutes) * 60_000
        self._open: int | None = None
        self._acc: Bar | None = None

    def push(self, bar: Bar) -> Bar | None:
        """Pridá bar grafu; vráti uzavretý bar vyššieho TF, ak sa práve uzavrel."""
        bucket = bar.time // self.tf_ms * self.tf_ms
        done: Bar | None = None
        if self._open is not None and bucket != self._open:
            done = self._acc
            self._acc = None
        self._open = bucket
        if self._acc is None:
            self._acc = Bar(bucket, bar.open, bar.high, bar.low, bar.close, bar.volume)
        else:
            a = self._acc
            self._acc = Bar(
                a.time, a.open, max(a.high, bar.high), min(a.low, bar.low), bar.close, a.volume + bar.volume
            )
        return done


class FvgDetector:
    """Na každom bare grafu povie, ktoré nové FVG sa na zapnutých TF práve uzavreli."""

    def __init__(self, tf_minutes: tuple[int, ...]) -> None:
        self._aggs = {m: TimeframeAggregator(m) for m in tf_minutes}
        self._recent: dict[int, list[Bar]] = {m: [] for m in tf_minutes}

    def on_bar(self, bar: Bar, min_size: float) -> list[FvgHit]:
        found: list[FvgHit] = []
        for minutes, agg in self._aggs.items():
            closed = agg.push(bar)
            if closed is None:
                continue
            recent = self._recent[minutes]
            recent.append(closed)
            if len(recent) > 3:
                del recent[:-3]
            if len(recent) == 3:
                hit = self._detect(recent, minutes, min_size)
                if hit is not None:
                    found.append(hit)
        return found

    @staticmethod
    def _detect(trio: list[Bar], minutes: int, min_size: float) -> FvgHit | None:
        """Trojica sviečok: medzera medzi 1. a 3. je fair value gap.

        Prostredná sviečka je impulz, ktorý medzeru vytvoril — jej telo sa nekontroluje,
        rovnako ako to robí `find_imbalance` v IBS.
        """
        far, _mid, near = trio
        if near.low > far.high and (near.low - far.high) >= min_size:
            return FvgHit(near.low, far.high, 1, minutes)
        if near.high < far.low and (far.low - near.high) >= min_size:
            return FvgHit(far.low, near.high, -1, minutes)
        return None
