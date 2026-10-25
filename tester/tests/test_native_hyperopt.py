"""Natívny hyperopt (`tester.native_hyperopt`): dávka C# na vláknach = Python emulátor, kritérium = TradebotPlanLoss.

Epocha je platná len vtedy, keď by ten istý config spustený vo webapp (emulátor MultiCharts) dal ten istý
súhrn. Preto sa tu dávka paralelných behov porovná s behmi po jednom aj s Python emulátorom, a loss
s pravidlami `TradebotPlanLoss` (dno na počet obchodov za rok, penalizácia za drawdown, smer kritéria).
"""

from __future__ import annotations


import pytest

from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades
from tradebot.core import load_profile
from tradebot.core.money import summary_money
from tradebot.core.types import INSTRUMENTS
from tester import engines
from tester.hyperopt import build_plan, overrides
from tester.native_hyperopt import UNUSABLE, NativeRunner, config_json, loss_of, run_search, summary_of, verify

INST = INSTRUMENTS["nas100_dukascopy"]
WINDOW = "20250101-20250401"
FEE = 0.0001


@pytest.fixture(scope="module")
def runner():
    from tradebot.adapters.csharp import bridge

    try:
        bridge._load_clr()
    except bridge.BridgeError as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")
    if not engines.one_minute_file(INST).exists():
        pytest.skip("chýbajú 1m dáta NAS100")
    return NativeRunner("orbnet", INST, 3, FEE, threads=4)


def _plan():
    return build_plan({"rrRatio": "0.5:4:0.25", "tradeDirection": "Both,Long only"}, strategy="orbnet")


def test_batch_on_threads_matches_single_runs_and_python(runner):
    plan = _plan()
    cfg, _ = load_profile("nas100_dukascopy_3m", strategy="orbnet", engine=engines.MULTICHARTS)
    points = [{"hp_rrRatio": rr, "hp_tradeDirection": d} for rr in (0.5, 1.0, 2.5, 4.0) for d in ("Both", "Long only")]
    configs = [config_json(cfg.to_dict(), type(cfg), plan, p) for p in points]
    batch = runner.run(configs, WINDOW)
    singles = [runner.run([c], WINDOW)[0] for c in configs]
    assert batch == singles                                   # vlákna nič nezdieľajú ani nemenia

    import pandas as pd

    m1 = pd.read_feather(engines.one_minute_file(INST))
    for p, res in list(zip(points, batch))[::3]:              # pár bodov aj proti Python emulátoru
        cfg_p = type(cfg).from_dict({**cfg.to_dict(), **overrides(plan, p)})
        a, b = (int(pd.Timestamp(x, tz="UTC").timestamp() * 1000) for x in WINDOW.split("-"))
        py, _ = emulate(cfg_p, INST, m1, 3, from_ms=a, to_ms=b, fee=FEE)
        want = summary_money(rows_from_trades(py.trades, INST, FEE), 10000)
        assert summary_of(res, INST, FEE, 10000) == want, p


def test_search_and_verification(runner):
    plan = _plan()
    found = run_search(runner, plan, None, WINDOW, epochs=16, batch=4, seed=3, log=lambda _s: None)
    assert len(found.epochs) == 16 and found.best is not None and found.best.is_best
    assert found.best.loss == min(e.loss for e in found.epochs if e.usable)
    assert 0 < found.distinct <= 16
    records = verify(runner, plan, None, found.best.params, WINDOW, windows=("20240904-20250904",))
    assert [r["settings"]["timerange"] for r in records] == ["20240904-20250904", WINDOW]
    tuned = next(r for r in records if r["tuned"])
    assert -found.best.loss == pytest.approx(tuned["result"]["break_even_pct"])


def test_loss_follows_plan_loss_rules():
    s = {"trades": 100, "winrate": 55.0, "pnl_pct": 12.0, "max_drawdown_pct": 8.0, "break_even_pct": 0.03}
    year = 365
    assert loss_of(s, build_plan({"rrRatio": "1:3:0.5"}, strategy="orbnet"), year) == -0.03
    assert loss_of(s, build_plan({"rrRatio": "1:3:0.5"}, strategy="orbnet", goal="winrate"), year) == -55.0
    assert loss_of(s, build_plan({"rrRatio": "1:3:0.5"}, strategy="orbnet", goal="drawdown"), year) == 8.0
    # dno na obchody je za rok a prepočíta sa na okno; pod ním spojitá penalizácia
    plan = build_plan({"rrRatio": "1:3:0.5"}, strategy="orbnet", min_trades=200)
    assert loss_of(s, plan, year) == UNUSABLE + 100
    assert loss_of(s, plan, 182) == -0.03
    # drawdown nad stropom kritérium nemení, len pripočíta penalizáciu
    plan = build_plan({"rrRatio": "1:3:0.5"}, strategy="orbnet", max_dd=5)
    assert loss_of(s, plan, year) == pytest.approx(-0.03 + UNUSABLE + 3.0)
    assert loss_of(None, plan, year) == UNUSABLE
    assert loss_of({**s, "break_even_pct": None}, build_plan({"rrRatio": "1:3:0.5"}, strategy="orbnet"), year) == UNUSABLE
