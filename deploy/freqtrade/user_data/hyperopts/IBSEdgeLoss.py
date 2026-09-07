"""Hyperopt loss, ktorý maximalizuje **break-even poplatok**, nie zisk.

Prečo nie zisk: edge stratégie je zhruba rovnako veľký ako poplatky (0,05 % na
stranu na Binance), takže čistý PnL je blízko nuly a hyperopt by v ňom ladil hlavne
šum. Break-even poplatok — koľko smie burza brať, aby konfigurácia vyšla na nulu —
je to isté číslo očistené o veľkosť pozície aj o počet obchodov:

    break-even = hrubý zisk / obchodovaný objem

Konfigurácia, ktorá zarobí rovnako pri polovičnom objeme, je jednoznačne lepšia,
a v tomto skóre to vidno okamžite. V čistom PnL nie.

Hrubý zisk sa počíta z cien, nie z `profit_abs`, takže skóre nezávisí od toho,
s akým `--fee` beží samotný hyperopt.

Použitie::

    freqtrade hyperopt --hyperopt-loss IBSEdgeLoss ...
"""

from __future__ import annotations

from datetime import datetime

from pandas import DataFrame

from freqtrade.optimize.hyperopt import IHyperOptLoss

#: Pod týmto počtom obchodov za 90 dní je výsledok šum. Nižšie než v
#: `IBSHyperOptLoss`, lebo štruktúrny filter počet obchodov legitímne polovičí
#: (~96 za rok, teda ~24 za 90 dní) — a práve taká konfigurácia je žiaduca.
MIN_TRADES_PER_90D = 15


class IBSEdgeLoss(IHyperOptLoss):
    """Maximalizuje hrubý edge na jednotku obchodovaného objemu."""

    @staticmethod
    def hyperopt_loss_function(
        results: DataFrame,
        trade_count: int,
        min_date: datetime,
        max_date: datetime,
        starting_balance: float,
        **kwargs,
    ) -> float:
        days = max((max_date - min_date).days, 1)
        required = max(3, int(MIN_TRADES_PER_90D * days / 90))

        if trade_count < required:
            # Spojitá penalizácia, nie plochá stena — hyperopt tak vidí, ktorým
            # smerom sa má vydať.
            return 1000.0 + (required - trade_count)

        direction = results["is_short"].map({True: -1.0, False: 1.0})
        gross = ((results["close_rate"] - results["open_rate"]) * results["amount"] * direction).sum()
        volume = (
            results["open_rate"] * results["amount"] + results["close_rate"] * results["amount"]
        ).sum()
        if volume <= 0:
            return 1000.0

        # Percentá na stranu, aby sa dalo priamo porovnať s poplatkom burzy.
        return -(gross / volume * 100.0)
