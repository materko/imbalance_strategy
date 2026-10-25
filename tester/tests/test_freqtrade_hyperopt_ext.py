"""Nadstavba nad Freqtrade hyperopt: sampler, kritérium cez okná v loss funkcii, Pareto z epoch,
výber podľa okolia, walk-forward a zlúčenie epoch pri pokračovaní.

Freqtrade sa nemení — všetko je plán (`TRADEBOT_HYPEROPT_PLAN`), loss funkcia a orchestrácia vo fronte
webapp. Posledný test pustí skutočný Freqtrade (krátke okná), aby bolo isté, že sa to spolu naozaj stretne.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta

import pytest

pytest.importorskip("freqtrade")
pd = pytest.importorskip("pandas")

from tradebot.adapters.freqtrade import hyperplan as hp
from tradebot.core.paths import REPO
from tester.hyperopt import Epoch, pareto_front

sys.path.insert(0, str(REPO / "deploy" / "freqtrade" / "user_data" / "hyperopts"))
from TradebotPlanLoss import TradebotPlanLoss  # noqa: E402


def _plan(**over) -> hp.Plan:
    data = {"strategy": "ibs", "knobs": {"rrRatio": {"low": 2, "high": 6}}}
    data.update(over)
    return hp.Plan.from_dict(data)


def test_plan_carries_sampler_and_windows():
    p = _plan(sampler="cmaes", windows=["20240101-20240201", "20240201-20240301"], aggregate="median")
    assert hp.Plan.from_dict(p.to_dict()) == p
    assert _plan().sampler is None and _plan().windows == ()
    assert hp.span(["20240201-20240301", "20240101-20240201"]) == "20240101-20240301"


def test_estimator_maps_plan_sampler_to_freqtrade(monkeypatch):
    import optuna

    assert hp.estimator(None) == "NSGAIIISampler"                     # predvolené ako doteraz
    assert hp.estimator(_plan(sampler="tpe")) == "TPESampler"
    assert hp.estimator(_plan(sampler="nsga2")) == "NSGAIISampler"
    assert isinstance(hp.estimator(_plan(sampler="random"), 3), optuna.samplers.RandomSampler)
    from tradebot.adapters.freqtrade.base import TradebotStrategyBase

    monkeypatch.setattr(hp, "plan_from_env", lambda: _plan(sampler="qmc"))
    assert TradebotStrategyBase.HyperOpt.generate_estimator(dimensions=[], random_state=1) == "QMCSampler"


def _results(rows: list[tuple[str, float]]):
    """(dátum otvorenia, zisk) -> výsledok v tvare, aký loss dostáva od Freqtradu."""
    return pd.DataFrame({
        "open_date": pd.to_datetime([d for d, _ in rows], utc=True),
        "profit_abs": [p for _, p in rows],
        "is_short": [False] * len(rows),
        "open_rate": [100.0] * len(rows),
        "close_rate": [100.0 + p for _, p in rows],
        "amount": [1.0] * len(rows),
    })


def _loss(results, plan, monkeypatch) -> float:
    monkeypatch.setattr("TradebotPlanLoss.plan_from_env", lambda: plan)
    return TradebotPlanLoss.hyperopt_loss_function(
        results=results, trade_count=len(results), min_date=datetime(2024, 1, 1),
        max_date=datetime(2024, 3, 1), starting_balance=10_000.0)


def test_loss_over_windows_takes_the_worst(monkeypatch):
    # január zarába, február stráca: na celom rozpätí je to plus, cez okná rozhoduje február
    rows = [(f"2024-01-{d:02d}", 2.0) for d in range(1, 25)] + [(f"2024-02-{d:02d}", -1.0) for d in range(1, 25)]
    res = _results(rows)
    okna = ["20240101-20240201", "20240201-20240301"]
    celok = _loss(res, _plan(min_trades=10), monkeypatch)
    najhorsie = _loss(res, _plan(min_trades=10, windows=okna), monkeypatch)
    jan = _loss(_results(rows[:24]), _plan(min_trades=10), monkeypatch)
    feb = _loss(_results(rows[24:]), _plan(min_trades=10), monkeypatch)
    assert celok < 0 < najhorsie and najhorsie == pytest.approx(max(jan, feb))
    assert _loss(res, _plan(min_trades=10, windows=okna, aggregate="mean"), monkeypatch) == pytest.approx((jan + feb) / 2)
    # dno na obchody sa prepočíta na okno: v okne bez obchodov je epocha mimo mantinelov
    prazdne = _loss(_results(rows[:24]), _plan(min_trades=10, windows=okna), monkeypatch)
    assert prazdne >= 1000


def test_pareto_front_from_epoch_metrics():
    def ep(n, loss, dd, trades):
        return Epoch(number=n, loss=loss, params={}, trades=trades, pnl_pct=0.0, winrate=50.0,
                     max_drawdown_pct=dd, profit_factor=1.0)

    epochs = [ep(1, -0.03, 20.0, 100), ep(2, -0.02, 10.0, 100), ep(3, -0.01, 15.0, 100), ep(4, 1005.0, 1.0, 2)]
    out = pareto_front(epochs, ["drawdown"])
    assert [e.number for e in out if e.pareto] == [1, 2]          # 3 prebije 2, 4 je mimo mantinelov
    assert out[0].values == [-0.03, 20.0]


@pytest.fixture
def ft_runner(tmp_path, monkeypatch):
    from tester import engines
    from tester.webapp import runner as runner_mod
    from tester.webapp.store import RunStore
    from tradebot.core.types import INSTRUMENTS

    if not engines.freqtrade_file(INSTRUMENTS["btcusdt_binance"], "3m").exists():
        pytest.skip("chýbajú dáta BTC/USDT:USDT")
    monkeypatch.setattr("tester.webapp.command.TMP_PROFILES", tmp_path / "profiles")
    monkeypatch.setattr("tester.webapp.runner.TMP_PROFILES", tmp_path / "profiles")
    monkeypatch.setattr("tester.hyperopt.PLANS_DIR", tmp_path / "plans")
    store = RunStore(tmp_path / "runs")
    br = runner_mod.BacktestRunner(store)
    zaradene: list[dict] = []
    monkeypatch.setattr(br, "submit", lambda params, settings, **kw: zaradene.append(settings))
    return br, store, zaradene


def test_freqtrade_queue_extensions_end_to_end(ft_runner):
    from tester.webapp import runner as runner_mod
    from tester.webapp.store import make_run_id

    br, store, zaradene = ft_runner
    params = runner_mod.default_params("golden_binance_btcusdt_3m", strategy="ibs")[0]
    W1, W2, W3 = "20260401-20260501", "20260501-20260601", "20260601-20260701"
    zaklad = {"strategy": "ibs", "pair": "BTC/USDT:USDT", "engine": "freqtrade", "exchange": "tester",
              "timeframe": "3m", "timerange": W2, "fee": 0.0005, "wallet": 10000.0, "timeframe_detail": "1m",
              "profile": "golden_binance_btcusdt_3m"}
    z = {"knobs": {"rrRatio": "1:4:0.5"}, "goal": "break_even", "min_trades": 12, "epochs": 6, "seed": 1,
         "verify": True, "sampler": "tpe", "jobs": 6}

    # hľadanie: okná v loss funkcii, Pareto z metrík, výber podľa okolia
    s1 = {**zaklad, "hyperopt": {**z, "windows": [W1, W2], "aggregate": "min", "objectives": ["drawdown"],
                                 "select": "plateau", "mode": "search"}}
    job = runner_mod.Job(id=make_run_id(params, s1), params=params, settings=s1, note="ext", user="t")
    br._run(job)
    assert job.status == "done", job.error
    rec = store.get(job.id)
    h = rec["settings"]["hyperopt"]
    assert h["windows"] == [W1, W2] and h["pareto"] and h["plateau_select"]["chosen"] == h["best"]["epoch"]
    log = "\n".join(job.log_lines)            # uložený log je skrátený
    assert "--timerange 20260401-20260601" in log and "Using optuna sampler TPESampler" in log
    assert [(s["timerange"], s["hyperopt_run"]["tuned"]) for s in zaradene[:2]] == [(W1, True), (W2, True)]
    epochs = store.extra(job.id, "epochs.json")
    assert len(epochs) == 6 and all("values" in e for e in epochs)

    # pokračovanie = zlúčenie: nový beh s iným seedom, epochy predošlého hľadania pred novými
    zaradene.clear()
    s2 = {**zaklad, "hyperopt": {**z, "windows": [W1, W2], "continue_from": job.id, "epochs": 4}}
    job2 = runner_mod.Job(id=make_run_id(params, s2), params=params, settings=s2, note="dalej", user="t")
    br._run(job2)
    assert job2.status == "done", job2.error
    h2 = store.get(job2.id)["settings"]["hyperopt"]
    assert h2["merged"] == 6 and h2["epochs_done"] == 10
    zlucene = store.extra(job2.id, "epochs.json")
    assert [e["params"] for e in zlucene[:6]] == [e["params"] for e in epochs]

    # walk-forward: hyperopt na N, víťaz ako backtest na N+1 — ten istý výsledok ako obyčajný beh
    zaradene.clear()
    s3 = {**zaklad, "hyperopt": {**z, "windows": [W1, W2, W3], "mode": "walkforward", "epochs": 4}}
    job3 = runner_mod.Job(id=make_run_id(params, s3), params=params, settings=s3, note="wf", user="t")
    br._run(job3)
    assert job3.status == "done", job3.error
    wf = store.get(job3.id)["settings"]["hyperopt"]["walk_forward"]
    assert [(f["train"], f["test"]) for f in wf["folds"]] == [([W1], W2), ([W2], W3)]
    assert wf["verdict"].startswith("WALK-FORWARD") and zaradene == []
    f0 = wf["folds"][0]
    beh = runner_mod.Job(id="20260101-000000-abcdef", params={**params, **f0["params"]},
                         settings={**zaklad, "timerange": W2}, note="kontrola", user="t")
    br._run(beh)
    assert beh.status == "done", beh.error
    kontrola = store.get(beh.id)["result"]
    for k in ("trades", "pnl_abs", "break_even_pct", "winrate"):
        assert kontrola[k] == f0["result"][k], k
