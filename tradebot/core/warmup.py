"""Predhistória (warmup) — bary grafu pre stratégiu a vlastná predhistória indikátorov na vyššom TF.

Sú dve rôzne veci a nemiešajú sa:

1. **Predhistória grafu** (`Warmup.add`) — bary grafu pred prvým signálom: okná histórie,
   ATR, pivoty. Výsledok `Warmup.chart_bars` je `Engine.required_history`; Freqtrade adaptér
   z neho robí `startup_candle_count` (aspoň 300 z triedy). Stavová logika (dni S/R úrovní,
   predošlá seansa, životnosť zón) sa sem **nepripočítava** — tak to bolo vždy a tak to
   zostáva (rozhodnutie 2026-09-17).
2. **Vlastná predhistória indikátora na vyššom TF** (`Warmup.add_seeded`) — Supertrend
   60m na 3m grafe nepotrebuje 820 barov grafu, ale 40 hodinových barov. Tie sa mu dajú
   **pred prvým barom grafu** z dát pred začiatkom behu (`seed_engine`), takže predhistória
   grafu kvôli nemu nerastie. Koľko barov, hovorí `warmup_bars` indikátora.

### Rekurzívne priemery (RMA/EMA) sa neustália nikdy úplne
Pine `ta.rma` aj `ta.ema` štartujú z SMA prvých `n` hodnôt a potom každá nová hodnota
pridá váhu `alpha`. Štartovacia hodnota má po `k` ďalších baroch váhu ``(1 − alpha)^k``;
za ustálený sa priemer považuje, keď tá váha klesne pod `SEED_WEIGHT` (5 %):

    bary = n + ceil( ln(SEED_WEIGHT) / ln(1 − alpha) )

RMA(10) → 10 + 29 = 39, RMA(14) → 14 + 41 = 55, EMA(26) → 26 + 39 = 65. Pri 5 % je
chyba ATR po rozbehu rádovo percento (rozdiel SMA štartu od „pravého" ATR býva desiatky
percent, z toho ostane 5 %). Tesnejšia tolerancia rastie s logaritmom: 1 % by bolo
RMA(10) → 54 barov.

### Seeding bez pohľadu dopredu
`seed_engine(engine, frame, first_ms)` vezme z `frame` (1m alebo TF grafu, stĺpce `date`
UTC + OHLCV) **len riadky pred `first_ms`** — časom otvorenia prvého baru, ktorý engine
dostane —, poskladá z nich bary TF indikátora výhradne cez `tradebot.core.candles.resample_ohlcv`
a indikátoru dá:

* posledných `bars` **uzavretých** periód (perióda končí najneskôr na `first_ms`; hľadá sa
  s rezervou `SEED_SLACK_DAYS` na víkendy a diery, perióda bez baru sa nepočíta) — prejdú
  výpočtom ako na živom grafe,
* rozpracovanú periódu, v ktorej `first_ms` leží (bary grafu od jej začiatku po `first_ms`),
  ako otvorený stav agregátora — prvý HTF bar behu je tak celý, nie useknutý.

Stav indikátora na prvom bare grafu je potom ten istý, aký by mal po spracovaní tých istých
barov naživo; dáta od `first_ms` ďalej ho neovplyvnia. Keď dáta pred začiatkom nie sú
(začiatok archívu), indikátor dostane, čo je, a dobehne sa na grafe — kým nemá `bars`
barov svojho TF, hlási „rozbieha sa" a smer nepovolí.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import Bar

__all__ = [
    "SEED_WEIGHT",
    "decay_bars",
    "sma_bars",
    "rma_bars",
    "ema_bars",
    "on_chart",
    "SeedFn",
    "WarmupNeed",
    "Warmup",
    "seed_engine",
]

#: Váha štartovacej hodnoty rekurzívneho priemeru, pod ktorú musí klesnúť (5 %).
SEED_WEIGHT = 0.05

_MIN_MS = 60_000
#: Rezerva dát na seeding za víkendy, sviatky a výpadky: periódy bez baru neexistujú,
#: takže `bars` barov TF indikátora môže siahať ďalej než `bars × TF`.
SEED_SLACK_DAYS = 4

#: `seed(uzavreté bary TF indikátora, rozpracovaný bar alebo None)` — volá sa raz, pred prvým barom.
SeedFn = Callable[[Sequence["Bar"], "Bar | None"], None]


def decay_bars(alpha: float, weight: float = SEED_WEIGHT) -> int:
    """Koľko barov trvá, kým váha štartovacej hodnoty klesne pod `weight`."""
    if alpha >= 1.0:
        return 0
    if alpha <= 0.0:
        raise ValueError("alpha musí byť kladná")
    return math.ceil(math.log(weight) / math.log(1.0 - alpha))


def sma_bars(length: int) -> int:
    """Kĺzavé okno (SMA, highest/lowest, pivot): presne `length` barov, potom je hodnota presná."""
    return max(1, int(length))


def rma_bars(length: int) -> int:
    """Pine `ta.rma` (Wilder, ATR, RSI, DMI): SMA štart + dozvuk s `alpha = 1/n`."""
    n = max(1, int(length))
    return n + decay_bars(1.0 / n)


def ema_bars(length: int) -> int:
    """Pine `ta.ema`: SMA štart + dozvuk s `alpha = 2/(n+1)`."""
    n = max(1, int(length))
    return n + decay_bars(2.0 / (n + 1))


def on_chart(bars: int, tf_minutes: int, chart_tf_minutes: int) -> int:
    """`bars` barov TF `tf_minutes` → bary grafu (s jedným HTF barom navyše za neúplnú periódu).

    Len informácia („koľko by to bolo na grafe") — seeded indikátor predhistóriu grafu nezväčšuje.
    """
    bars = max(0, int(bars))
    chart = max(1, int(chart_tf_minutes))
    tf = max(chart, int(tf_minutes))
    if tf == chart:
        return bars
    return (bars + 1) * math.ceil(tf / chart)


@dataclass(frozen=True, slots=True)
class WarmupNeed:
    """Jedna položka: čo (`name`), koľko barov (`bars`) a na akom TF (`tf_minutes`).

    S `seed` je to indikátor s vlastnou predhistóriou (do `chart_bars` sa nepočíta).
    """

    name: str
    bars: int
    tf_minutes: int
    seed: SeedFn | None = field(default=None, compare=False, repr=False)

    @property
    def seeded(self) -> bool:
        return self.seed is not None

    def chart_bars(self, chart_tf_minutes: int) -> int:
        return on_chart(self.bars, self.tf_minutes, chart_tf_minutes)

    @property
    def span_ms(self) -> int:
        """Ako ďaleko pred prvým barom hľadať `bars` uzavretých periód (s rezervou na diery v dátach)."""
        if not self.seeded:
            return 0
        return 2 * (self.bars + 1) * self.tf_minutes * _MIN_MS + SEED_SLACK_DAYS * 1440 * _MIN_MS


@dataclass
class Warmup:
    """Zoznam potrieb engine-u; `chart_bars` je `required_history`, `seeds` idú do `seed_engine`.

    ``Warmup(3).add("ATR 14", rma_bars(14)).add_seeded("Supertrend 10", 40, 60, gate.seed_st)``
    """

    chart_tf_minutes: int
    needs: list[WarmupNeed] = field(default_factory=list)

    def add(self, name: str, bars: int, tf_minutes: int | None = None) -> "Warmup":
        """Predhistória v baroch grafu (indikátor na TF grafu, okno histórie)."""
        tf = int(tf_minutes) if tf_minutes is not None else int(self.chart_tf_minutes)
        self.needs.append(WarmupNeed(name, int(bars), tf))
        return self

    def add_seeded(self, name: str, bars: int, tf_minutes: int, seed: SeedFn) -> "Warmup":
        """Indikátor na vlastnom TF: `bars` barov toho TF dostane pred behom cez `seed`."""
        self.needs.append(WarmupNeed(name, int(bars), int(tf_minutes), seed))
        return self

    @property
    def chart_needs(self) -> list[WarmupNeed]:
        return [n for n in self.needs if not n.seeded]

    @property
    def seeds(self) -> list[WarmupNeed]:
        return [n for n in self.needs if n.seeded]

    @property
    def chart_bars(self) -> int:
        return max((n.chart_bars(self.chart_tf_minutes) for n in self.chart_needs), default=1) or 1

    @property
    def seed_span_ms(self) -> int:
        """Ako ďaleko pred prvým barom musia siahať dáta na seeding (0 = netreba)."""
        return max((n.span_ms for n in self.seeds), default=0)

    def describe(self) -> str:
        """Napr. ``okno historie: 264; Supertrend 10 @60m: 40 vlastnych`` — do logu (ASCII)."""
        parts = []
        for n in self.needs:
            if n.seeded:
                parts.append(f"{n.name} @{n.tf_minutes}m: {n.bars} vlastnych")
            elif n.tf_minutes == self.chart_tf_minutes:
                parts.append(f"{n.name}: {n.bars}")
            else:
                parts.append(f"{n.name} @{n.tf_minutes}m: {n.bars} -> {n.chart_bars(self.chart_tf_minutes)}")
        return "; ".join(parts)


def seed_engine(engine: Any, frame: Any, first_ms: int) -> dict[str, int]:
    """Seeduje indikátory engine-u s vlastnou predhistóriou z dát pred `first_ms`.

    `frame` je pandas DataFrame (`date` UTC, `open`/`high`/`low`/`close`/`volume`) v TF,
    ktorý delí TF grafu (1m alebo TF grafu); riadky od `first_ms` ďalej sa ignorujú.
    Môže to byť aj funkcia ``need -> DataFrame | None``, keď má každý indikátor iný zdroj
    (Freqtrade dry/live: uzavreté bary TF indikátora od burzy + rozpracovaná perióda v TF
    grafu). Taký frame smie mať bar TF indikátora len pre **uzavretú** periódu (začiatok pred
    periódou `first_ms`) — riadok s časom pred `first_ms` sa berie ako hotový.
    Vracia ``{meno: počet uzavretých barov vlastného TF}`` (na log a testy). Engine bez
    `warmup` alebo bez seeded položiek vráti `{}`.
    """
    warmup = getattr(engine, "warmup", None)
    seeds = warmup.seeds if warmup is not None else []
    if not seeds:
        return {}
    source = frame if callable(frame) else (lambda need: frame)

    import pandas as pd

    from .candles import resample_ohlcv
    from .types import Bar

    cols = ["date", "open", "high", "low", "close", "volume"]
    first = pd.Timestamp(int(first_ms), unit="ms", tz="UTC")
    report: dict[str, int] = {}
    for need in seeds:
        data = source(need)
        if data is None or len(data) == 0:
            report[need.name] = 0
            continue
        dates = pd.to_datetime(data["date"], utc=True)
        ms = need.tf_minutes * _MIN_MS
        period = int(first_ms) // ms * ms          # rozpracovaná perióda, v ktorej beh začína
        start = pd.Timestamp(period - need.span_ms, unit="ms", tz="UTC")
        mask = ((dates >= start) & (dates < first)).to_numpy()
        part = data.loc[mask, cols].reset_index(drop=True)
        part["date"] = pd.to_datetime(part["date"], utc=True)
        htf = resample_ohlcv(part.sort_values("date"), need.tf_minutes) if len(part) else part
        closed: list[Bar] = []
        partial: Bar | None = None
        if len(htf):
            ts = (htf["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).tolist()
            for t, row in zip(ts, htf.itertuples(index=False)):
                bar = Bar(time=int(t), open=float(row.open), high=float(row.high), low=float(row.low),
                          close=float(row.close), volume=float(row.volume))
                if bar.time < period:
                    closed.append(bar)
                elif bar.time == period:
                    partial = bar
        closed = closed[-need.bars:] if need.bars > 0 else []
        need.seed(closed, partial)
        report[need.name] = len(closed)
    return report
