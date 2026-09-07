"""Hyperopt loss so **spodným limitom na počet obchodov**.

Prečo vlastná: štandardné funkcie (Calmar, Sharpe, Sortino) počet obchodov nijako
nestrážia. Na tejto stratégii to hneď vypláchlo — Calmar vyhlásil za víťaza epochu
so **7 obchodmi za 90 dní** a +17 %, len preto, že mala malý drawdown. Sedem obchodov
o stratégii nehovorí nič.

Skóre je Calmar (ročný výnos delený max drawdownom), ale epochy pod `MIN_TRADES`
dostanú tvrdú penalizáciu úmernú tomu, ako veľmi limit nesplnili. Tým sa nezahodia
úplne (hyperopt potrebuje spojitý signál, aby vedel, ktorým smerom ísť), ale nikdy
nevyhrajú nad slušne obchodujúcou konfiguráciou.

Použitie::

    freqtrade hyperopt --hyperopt-loss IBSHyperOptLoss ...
"""

from __future__ import annotations

from datetime import datetime

from pandas import DataFrame

from freqtrade.optimize.hyperopt import IHyperOptLoss

#: Referencia: manuálny prieskum v TradingView dal 39-40 obchodov za 90 dní
#: a 174 za rok. Pod tento počet už výsledok nie je čím podložiť.
MIN_TRADES_PER_90D = 25


class IBSHyperOptLoss(IHyperOptLoss):
    """Calmar s tvrdým dnom na počte obchodov."""

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
            # Čím ďalej od limitu, tým horšie - hyperopt tak vidí smer,
            # ktorým sa má vydať, namiesto plochej steny.
            return 1000.0 + (required - trade_count)

        total_profit = results["profit_abs"].sum()
        if total_profit <= 0:
            # Stratové konfigurácie radíme podľa toho, ako veľmi stratové sú.
            return 100.0 - total_profit / starting_balance

        # Max drawdown z priebežnej krivky kapitálu.
        equity = starting_balance + results["profit_abs"].cumsum()
        peak = equity.cummax()
        max_dd = float(((peak - equity) / peak).max())

        annual = (total_profit / starting_balance) * (365.0 / days)
        calmar = annual / max(max_dd, 0.01)
        return -calmar
