"""Hyperopt loss podľa **plánu testera** — kritérium aj mantinely z jedného JSONu.

Kritérium je to, čo z ladenia robí odpoveď. „Najvyšší winrate pri drawdowne do 15 %" je
niečo iné než „najvyšší zisk pri tom istom limite" a bez toho, aby to bolo povedané, sa
optimum nedá určiť. Tester si preto vyberá z tých istých štyroch kritérií ako pri sweepe
a plán ich nesie spolu s priestorom, takže sa nemôžu rozísť:

    {"goal": "winrate", "max_dd": 15.0, "min_trades": 20, "knobs": {...}}

Kritériá:

``break_even`` (predvolené)
    Najvyšší break-even poplatok — koľko smie burza brať, aby beh vyšiel na nulu.
    Hrubý zisk delený obchodovaným objemom, počítaný z cien, takže nezávisí ani od
    veľkosti pozície, ani od `--fee`, s ktorým hyperopt beží. Edge tejto stratégie je
    rádovo taký veľký ako poplatky, takže v čistom PnL by sa ladil hlavne šum.
``profit``
    Najvyšší čistý zisk. Winrate sa neriešia.
``winrate``
    Najvyšší podiel ziskových obchodov.
``drawdown``
    Najnižší max drawdown.

Mantinely (obe voliteľné) sa neuplatňujú ako zákaz, ale ako penalizácia rastúca so
vzdialenosťou od limitu. Plochá stena je pre optimalizátor slepá — nevidí, ktorým
smerom sa má vydať; spojitá penalizácia mu smer necháva a zároveň zabezpečí, že
konfigurácia mimo mantinelov nikdy neprebije tú, čo ich drží:

``min_trades``
    Prepočíta sa na dĺžku okna (zadané číslo platí na rok). Bez dolného limitu na počet
    obchodov vyhlási optimalizátor za víťaza epochu so siedmimi obchodmi za 90 dní —
    stalo sa, viď docs/merania/HYPEROPT_btcusdt_2026-09-04.md.
``max_dd``
    Strop na max drawdown v percentách.

Použitie (dopĺňa `tester.hyperopt`, ručne netreba)::

    TRADEBOT_HYPEROPT_PLAN=... freqtrade hyperopt --hyperopt-loss TradebotPlanLoss \\
        --spaces plan --analyze-per-epoch ...
"""

from __future__ import annotations

from datetime import datetime

from pandas import DataFrame

from freqtrade.optimize.hyperopt_loss.hyperopt_loss_interface import IHyperOptLoss

from tradebot.adapters.freqtrade.hyperplan import plan_from_env

#: Keď plán počet obchodov nezadá, platí toto — pod ním výsledok nie je čím podložiť.
#: Referencia: manuálny prieskum v TradingView dal 174 obchodov za rok.
DEFAULT_MIN_TRADES_PER_YEAR = 60

#: Skóre epochy, ktorá sa nedá vyhodnotiť (žiadny objem, prázdny výsledok).
UNUSABLE = 1000.0


def _max_drawdown(results: DataFrame, starting_balance: float) -> float:
    """Max drawdown ako podiel (0,15 = 15 %) z priebežnej krivky kapitálu."""
    equity = starting_balance + results["profit_abs"].cumsum()
    peak = equity.cummax()
    return float(((peak - equity) / peak).max())


def _break_even_pct(results: DataFrame) -> float | None:
    """Break-even poplatok v % na stranu — to isté číslo, aké ukazuje história behov."""
    direction = results["is_short"].map({True: -1.0, False: 1.0})
    gross = ((results["close_rate"] - results["open_rate"]) * results["amount"] * direction).sum()
    volume = ((results["open_rate"] + results["close_rate"]) * results["amount"]).sum()
    return None if volume <= 0 else float(gross / volume * 100.0)


class TradebotPlanLoss(IHyperOptLoss):
    """Kritérium a mantinely z plánu testera."""

    @staticmethod
    def hyperopt_loss_function(
        results: DataFrame,
        trade_count: int,
        min_date: datetime,
        max_date: datetime,
        starting_balance: float,
        **kwargs,
    ) -> float:
        plan = plan_from_env()
        goal = (plan.goal if plan else None) or "break_even"
        days = max((max_date - min_date).days, 1)

        za_rok = plan.min_trades if plan and plan.min_trades else DEFAULT_MIN_TRADES_PER_YEAR
        treba = max(3, int(za_rok * days / 365))
        if trade_count < treba:
            return UNUSABLE + (treba - trade_count)

        if goal == "winrate":
            skore = float((results["profit_abs"] > 0).mean() * 100.0)
        elif goal == "profit":
            skore = float(results["profit_abs"].sum() / starting_balance * 100.0)
        elif goal == "drawdown":
            # Menej je lepšie, takže znamienko je opačné než u ostatných kritérií.
            skore = -float(_max_drawdown(results, starting_balance) * 100.0)
        else:
            be = _break_even_pct(results)
            if be is None:
                return UNUSABLE
            skore = be

        # Mantinel na drawdown až nakoniec: kritérium sa ním nemení, len sa pripočíta
        # penalizácia, ktorá rastie s prekročením - epocha mimo limitu tak neprebije
        # tú, čo limit drží, ale optimalizátor stále vidí, ktorým smerom je lepšie.
        loss = -skore
        if plan and plan.max_dd:
            dd = _max_drawdown(results, starting_balance) * 100.0
            if dd > plan.max_dd:
                loss += UNUSABLE + (dd - plan.max_dd)
        return loss
