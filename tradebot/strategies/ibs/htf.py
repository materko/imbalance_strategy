"""Okno detekčného TF (`zoneDetectionTF`) — to, čo IBS Pine ťahá cez `request.security`.

`HTFFeeder` je jediná implementácia toho, KEDY a Z ČOHO sa okno skladá. Freqtrade mu dá
predpočítané bary a SMA objemu z informative dataframe (`load`), MultiCharts kŕmi
uzavreté bary Data2 po jednom (`feed`); `window_for` je pre oba rovnaké. Predtým bola
tá logika dvakrát (runner Freqtrade, runner MC) a každá odchýlka by rozišla platformy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from tradebot.core.types import Bar

if TYPE_CHECKING:
    from .config import IBSConfig

__all__ = ["HTFWindow", "htf_window_opens", "HTFFeeder"]


@dataclass(frozen=True, slots=True)
class HTFWindow:
    """Okno posledných uzavretých barov detekčného TF (`zoneDetectionTF`).

    Pine si ho ťahá jedným `request.security(...)` na riadku 338 súboru
    pine/imbalance_strategy_FULL.pine, s offsetom ``[1]``..``[4]`` a ``lookahead_off``.
    ``bars[0]`` je teda Pine ``[1]`` — posledný UZAVRETÝ HTF bar, nie ten rozpracovaný.
    Preto tu nikdy nedochádza k repaintu.
    """

    REQUIRED_BARS: ClassVar[int] = 4

    bars: tuple[Bar, ...]  # dĺžka 4: Pine [1], [2], [3], [4]
    vol_sma: float  # ta.sma(volume, volSmaLen)[1]

    def __post_init__(self) -> None:
        if len(self.bars) != self.REQUIRED_BARS:
            raise ValueError(
                f"HTFWindow potrebuje presne {self.REQUIRED_BARS} barov, dostal {len(self.bars)}"
            )


def htf_window_opens(ts_ms: int, chart_tf_ms: int, htf_ms: int, count: int = HTFWindow.REQUIRED_BARS) -> list[int]:
    """Otváracie časy HTF barov, ktoré Pine `request.security` vidí na danom bare grafu.

    `ts_ms` je OTVÁRACÍ čas baru grafu; Pine vyhodnocuje bar pri jeho uzavretí, teda
    v čase ``ts_ms + chart_tf_ms``. S ``lookahead_off`` je vtedy "aktuálnym" HTF barom
    v security ten, ktorý sa naposledy UZAVREL::

        newest_close = floor(close_ms / htf_ms) * htf_ms      ->  open = newest_close - htf_ms

    Výraz v security (riadok 338 Pine) má navyše offset ``[1]``, takže ``bars[0]``
    je ešte o jeden HTF bar dozadu — spolu ``- 2 * htf_ms``.

    Keď sa mriežky neprekrývajú (3m graf / 5m detekcia), tento posun NIE JE konštantný
    voči ``ts_ms // htf_ms``: na bare 12:00 dá okno končiace 11:50, na 12:06 okno
    končiace 12:00 a na 12:12 okno končiace 12:05. Práve preto sa okno nesmie počítať
    z otváracieho času baru.
    """
    close_ms = ts_ms + chart_tf_ms
    newest = (close_ms // htf_ms) * htf_ms - 2 * htf_ms
    return [newest - i * htf_ms for i in range(count)]


class HTFFeeder:
    """Drží uzavreté bary detekčného TF a na bare grafu, kde sa práve uzavrela nová
    perióda, vráti `HTFWindow` — presne Pine `first5mTick`.

    Ktoré štyri bary to sú, počíta `htf_window_opens()` z ČASU UZAVRETIA baru grafu —
    nie z jeho otvorenia. Pri neprekrývajúcich sa mriežkach (3m graf / 5m detekcia)
    sa tie dve odpovede líšia a rozdiel bolo vidieť ako 104 zón oproti 77 v TradingView.
    """

    def __init__(self, cfg: "IBSConfig", chart_tf_minutes: int, *, keep: int | None = None) -> None:
        self.htf_ms = int(cfg.zoneDetectionTF) * 60_000
        self.step_ms = chart_tf_minutes * 60_000
        self.vol_sma_len = int(cfg.volSmaLen)
        #: otvárací čas HTF baru -> bar; SMA objemu za `volSmaLen` barov vrátane toho baru
        self.bars: dict[int, Bar] = {}
        self.vol_sma: dict[int, float] = {}
        self._volumes: list[float] = []
        self._prev_open: int | None = None
        #: koľko barov držať pri inkrementálnom kŕmení (`None` = všetko, backtest)
        self.keep = keep

    def load(self, bars: dict[int, Bar], vol_sma: dict[int, float]) -> None:
        """Predpočítané bary a SMA (Freqtrade: `rolling(volSmaLen).mean()`, NaN -> 0)."""
        self.bars = bars
        self.vol_sma = vol_sma

    def feed(self, bar: Bar) -> None:
        """Zaeviduje uzavretý bar detekčného TF (MultiCharts `Data2`).

        Volá sa len keď sa HTF bar naozaj **uzavrel**; priebežné aktualizácie
        posledného baru by narušili `vol_sma`.
        """
        if bar.time in self.bars:
            return
        self.bars[bar.time] = bar
        self._volumes.append(bar.volume)
        n = self.vol_sma_len
        if len(self._volumes) >= n:
            self.vol_sma[bar.time] = sum(self._volumes[-n:]) / n
        else:
            self.vol_sma[bar.time] = 0.0
        if self.keep is not None:
            if len(self._volumes) > self.keep:
                self._volumes = self._volumes[-self.keep:]
            if len(self.bars) > self.keep:
                for old in sorted(self.bars)[: len(self.bars) - self.keep]:
                    self.bars.pop(old, None)
                    self.vol_sma.pop(old, None)

    def window_for(self, ts_ms: int) -> HTFWindow | None:
        """Okno štyroch uzavretých HTF barov — ale len na bare, kde začala nová perióda."""
        htf_open = ts_ms // self.htf_ms * self.htf_ms
        is_new_period = self._prev_open is not None and htf_open != self._prev_open
        self._prev_open = htf_open
        if not is_new_period:
            return None
        opens = htf_window_opens(ts_ms, self.step_ms, self.htf_ms)
        if any(o not in self.bars for o in opens):
            return None
        return HTFWindow(tuple(self.bars[o] for o in opens), self.vol_sma.get(opens[0], 0.0))
