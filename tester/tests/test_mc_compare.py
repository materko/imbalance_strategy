"""Párovanie obchodov MultiCharts (log) so simulátorom — mc_compare."""

from __future__ import annotations

from datetime import datetime, timezone

from tester.compare.mc_compare import SimTradeRow, pair_trades
from tester.compare.mc_log_trades import McTrade


def sim(order, when, entry, outcome="WIN"):
    return SimTradeRow(order=order, placed=datetime.fromisoformat(when).replace(tzinfo=timezone.utc), entry=entry, qty=1.0, outcome=outcome)


def mc(order, bar, entry, pnl, intrabar=False):
    return McTrade(n=1, bar=bar, order=order, lots=1.0, entry=entry, pnl=pnl, intrabar=intrabar)


def test_paruje_podla_entry_a_datumu_a_hlasi_zvysok():
    s = [
        sim("LONG_1", "2025-01-06 16:24", 21674.91),                 # market vstup, MC entry o 2 body inde
        sim("LONG_2", "2025-01-13 16:33", 20634.69, "LOSS"),          # zavrety o 3 dni neskor
        sim("LONG_3", "2025-01-20 10:00", 21000.00),                  # v MC chyba
    ]
    m = [
        mc("LONG_9", "2025-01-06 16:30", 21676.59, 320.98, intrabar=True),
        mc("LONG_49", "2025-01-16 17:00", 20634.686, -341.72),
        mc("LONG_77", "2025-01-25 09:00", 21500.00, 10.0),            # v simulatore chyba
        mc("LONG_78", "2025-01-06 16:45", 21674.909, -5.0),           # blizsi entry, ale je to LOSS -> pár podľa entry, nie výsledku
    ]
    res = pair_trades(s, m, tolerance=5.0)
    paired = {a.order: b.order for a, b in res.pairs}
    assert paired == {"LONG_1": "LONG_78", "LONG_2": "LONG_49"}   # najblizsi entry vyhrava
    assert [x.order for x in res.sim_only] == ["LONG_3"]
    assert sorted(x.order for x in res.mc_only) == ["LONG_77", "LONG_9"]
    assert res.same_outcome == 1


def test_mc_obchod_pred_zadanim_alebo_prilis_neskoro_sa_nepáruje():
    s = [sim("LONG_1", "2025-03-10 10:00", 100.0)]
    m = [mc("A", "2025-03-09 10:00", 100.0, 1.0), mc("B", "2025-03-25 10:00", 100.0, 1.0)]
    res = pair_trades(s, m, tolerance=1.0, max_days=10)
    assert res.pairs == [] and len(res.sim_only) == 1 and len(res.mc_only) == 2
