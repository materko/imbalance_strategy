"""Otváracia sviečka z informatívneho TF — jediné miesto, kde sa rozhoduje, KTORÝ bar to je.

Prečo vôbec informatívny TF: zadanie hovorí **prvá 5-minútová sviečka**, ale vstupuje sa
na 1m, 2m alebo 3m grafe. Päť sa dvomi ani tromi nedelí, takže z barov 3m grafu by vyšlo
okno 9:30–9:36 — o pätinu širšie než tá sviečka, na ktorú sa pozerá obchodník. Hranica by
sa tak na každom TF volala rovnako a znamenala niečo iné.

Feeder preto drží uzavreté bary TF otváracej sviečky (Freqtrade ich dodá predpočítané cez
``load``, MultiCharts ich kŕmi po jednom z Data2 cez ``feed``) a na každom bare grafu
povie, ktorý z nich sa naposledy uzavrel. Engine si z nich vyberie ten, ktorý začína na
otvorení seansy; dedupuje podľa otváracieho času, takže mu neprekáža, že ten istý bar
dostane viackrát.
"""

from __future__ import annotations

from dataclasses import dataclass

from tradebot.core.types import Bar

__all__ = ["ClosedHtfBar", "OpeningFeeder"]


@dataclass(frozen=True)
class ClosedHtfBar:
    """Posledný **uzavretý** bar informatívneho TF k času zavretia baru grafu.

    ``open_ms`` je jeho otvárací čas — engine podľa neho pozná, či je to práve tá
    otváracia sviečka seansy. Nikdy to nie je rozpracovaný bar, takže sa nerepaintuje.
    """

    bar: Bar
    open_ms: int


class OpeningFeeder:
    """Uzavreté bary TF otváracej sviečky. Jedna implementácia pre oba enginy."""

    def __init__(self, cfg, chart_tf_minutes: int, *, keep: int | None = None) -> None:
        self.htf_ms = cfg.openingMinutes.minutes * 60_000
        self.step_ms = max(1, int(chart_tf_minutes)) * 60_000
        #: otvárací čas baru -> bar
        self.bars: dict[int, Bar] = {}
        #: SMA objemu na HTF stratégia nepoužíva (objemový filter beží na baroch grafu);
        #: pole tu je preto, že ho číta generický `MCRunner.htf_vol_sma`.
        self.vol_sma: dict[int, float] = {}
        #: koľko barov držať pri inkrementálnom kŕmení (`None` = všetko, backtest)
        self.keep = keep

    def limit_history(self) -> None:
        """MultiCharts kŕmi bar po bare celú históriu grafu — držať treba len pár posledných."""
        self.keep = 8

    def load(self, bars: dict[int, Bar], vol_sma: dict[int, float] | None = None) -> None:
        """Predpočítané bary z informative dataframe (Freqtrade)."""
        self.bars = bars
        self.vol_sma = vol_sma or {}

    def feed(self, bar: Bar) -> None:
        """Zaeviduje uzavretý bar informatívneho TF (MultiCharts `Data2`)."""
        if bar.time in self.bars:
            return
        self.bars[bar.time] = bar
        if self.keep is not None and len(self.bars) > self.keep:
            for old in sorted(self.bars)[: len(self.bars) - self.keep]:
                self.bars.pop(old, None)
                self.vol_sma.pop(old, None)

    def window_for(self, ts_ms: int) -> ClosedHtfBar | None:
        """Naposledy uzavretý HTF bar v okamihu, keď sa zavrel bar grafu ``ts_ms``.

        Počíta sa z času **zavretia** baru grafu (``ts_ms + step_ms``), nie z jeho
        otvorenia — pri neprekrývajúcich sa mriežkach (3m graf / 5m sviečka) sa tie dve
        odpovede líšia. Na 3m grafe sa bar 9:33–9:36 zavrie o 9:36 a sviečka 9:30–9:35
        je vtedy už uzavretá; na 2m grafe to platí od baru končiaceho 9:36, na 1m od
        baru končiaceho 9:35.
        """
        close_ms = ts_ms + self.step_ms
        open_ms = (close_ms // self.htf_ms) * self.htf_ms - self.htf_ms
        bar = self.bars.get(open_ms)
        return ClosedHtfBar(bar, open_ms) if bar is not None else None
