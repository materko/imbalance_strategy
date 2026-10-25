"""Režimy natívneho hyperoptu a natívne behy vo fronte / cez API (`tester.native`, `tester.native_hyperopt`).

Kritérium cez viac okien, viac cieľov (Pareto), výber podľa okolia, walk-forward, pokračovanie; bod celku
vo fronte webapp natívne (súhrn = Python emulátor) a `/api/native/backtests` bez histórie.
"""

from __future__ import annotations

import json

import pytest

from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tester import engines
from tester.hyperopt import build_plan, overrides, verdict
from tester.native import NativeRunner, summary_of
from tester.native_hyperopt import (UNUSABLE, config_json, loss_of, run_search, verify, walk_forward)

INST = INSTRUMENTS["nas100_dukascopy"]
FEE = 0.0001
W1, W2, W3 = "20250101-20250301", "20250301-20250501", "20250501-20250701"


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


def _plan(**kw):
    return build_plan({"rrRatio": "0.5:4:0.25", "nyRangeMinutes": "5:60:5"}, strategy="orbnet", **kw)


def _quiet(_s: str) -> None:
    pass


def test_multi_window_loss_is_the_worst_window(runner):
    found = run_search(runner, _plan(), None, W2, epochs=8, batch=4, seed=1, windows=(W1, W2), log=_quiet)
    for e in found.epochs:
        assert set(e.windows) == {W1, W2}
        assert e.loss == max(w["loss"] for w in e.windows.values())
        assert e.trades == sum(int(w["trades"] or 0) for w in e.windows.values())
    med = run_search(runner, _plan(), None, W2, epochs=4, batch=4, seed=1, windows=(W1, W2, W3),
                     aggregate_how="median", log=_quiet)
    e = med.epochs[0]
    assert e.loss == sorted(w["loss"] for w in e.windows.values())[1]


def test_objectives_give_pareto_front(runner):
    found = run_search(runner, _plan(), None, W1, epochs=16, batch=8, seed=2, sampler="nsga2",
                       objectives=("drawdown", "trades"), log=_quiet)
    assert found.objectives == ("break_even", "drawdown", "trades")
    assert found.pareto and all(len(e.values) == 3 for e in found.epochs)
    assert all(e.values[0] == e.loss for e in found.epochs)        # prvý cieľ = kritérium plánu
    assert {e.number for e in found.epochs if e.pareto} == set(found.pareto)
    with pytest.raises(ValueError, match="CMA-ES"):
        run_search(runner, _plan(), None, W1, epochs=4, sampler="cmaes", objectives=("drawdown",), log=_quiet)


def test_plateau_select_picks_best_neighbourhood(runner):
    found = run_search(runner, _plan(), None, W1, epochs=24, batch=8, seed=3, select="plateau", log=_quiet)
    info = found.plateau
    assert info and found.best is not None and found.best.number == info["chosen"]
    vybrany = min(info["candidates"], key=lambda c: c["robust"])
    assert vybrany["epoch"] == info["chosen"] and vybrany["neighbours"] > 0
    for c in info["candidates"]:     # robustné skóre = priemer epochy a susedov
        assert c["robust"] == pytest.approx(sum([c["loss"], *(p["loss"] for p in c["points"])]) / (1 + len(c["points"])))


def test_walk_forward_tests_on_unseen_window(runner):
    plan = _plan()
    wf = walk_forward(runner, plan, None, [W1, W2, W3], epochs=8, batch=4, seed=4, log=_quiet)
    assert [(f["train"], f["test"]) for f in wf.folds] == [([W1], W2), ([W2], W3)]
    cfg, _ = load_profile("nas100_dukascopy_3m", strategy="orbnet", engine=engines.MULTICHARTS)
    for f in wf.folds:
        res = runner.run([config_json(cfg.to_dict(), type(cfg), plan, f["hp"])], f["test"])[0]
        assert summary_of(res, INST, FEE, 10000) == f["result"]
    assert wf.verdict.startswith("WALK-FORWARD") and len(wf.epochs) == 16
    assert {e.fold for e in wf.epochs} == {0, 1}
    ank = walk_forward(runner, plan, None, [W1, W2, W3], epochs=4, batch=4, seed=4, anchored=True, log=_quiet)
    assert ank.folds[1]["train"] == [W1, W2]


def test_continue_puts_old_epochs_into_study(runner):
    prvy = run_search(runner, _plan(), None, W1, epochs=8, batch=4, seed=5, log=_quiet)
    dalsi = run_search(runner, _plan(), None, W1, epochs=8, batch=4, seed=6, log=_quiet,
                       warm=[e.to_dict() for e in prvy.epochs])
    assert [e.number for e in dalsi.epochs] == list(range(1, 17))
    assert [e.params for e in dalsi.epochs[:8]] == [e.params for e in prvy.epochs]
    assert dalsi.best.loss <= prvy.best.loss                           # staré epochy sa do výberu rátajú


def test_verify_marks_all_tuned_windows(runner):
    plan = _plan()
    found = run_search(runner, plan, None, W2, epochs=4, batch=4, seed=7, windows=(W1, W2), log=_quiet)
    recs = verify(runner, plan, None, found.best.params, [W1, W2], windows=(W3,))
    assert [(r["settings"]["timerange"], r["tuned"]) for r in recs] == [(W3, False), (W1, True), (W2, True)]
    text = verdict(recs, [W1, W2])
    assert "ladenych" in text or "VITAZ PREZIL" in text


def test_queue_point_runs_natively_with_same_summary_as_python(runner, tmp_path, monkeypatch):
    """Bod celku (sweep) C# stratégie ide vo fronte natívne — súhrn, obchody aj séria ako Python emulátor."""
    from tester import native
    from tester.webapp import results as results_mod
    from tester.webapp import runner as runner_mod
    from tester.webapp.command import write_profile

    params = runner_mod.default_params("nas100_dukascopy_3m", strategy="orbnet", engine="multicharts")[0]
    settings = {"strategy": "orbnet", "pair": "NAS100/USD", "engine": "multicharts", "timeframe": "3m",
                "timerange": W1, "fee": FEE, "wallet": 10000.0, "timeframe_detail": "1m",
                "profile": "nas100_dukascopy_3m", "sweep": {"id": "test", "values": {}}}
    profile = write_profile("test-native", params, "nas100_dukascopy", "orbnet", directory=tmp_path)
    assert native.can_run(settings)
    assert not native.can_run({k: v for k, v in settings.items() if k != "sweep"})     # beh s grafom ostáva Python
    monkeypatch.setenv("TRADEBOT_NATIVE_BATCH", "0")
    assert not native.can_run(settings)
    monkeypatch.delenv("TRADEBOT_NATIVE_BATCH")
    s_n, rows_n, series_n, _ = native.run_record(params, settings, profile)
    s_p, rows_p, series_p, _ = results_mod.run_multicharts(params, settings, profile, log=_quiet)
    assert s_n.pop("native") is True
    assert s_n == s_p and rows_n == rows_p and series_n == series_p


def test_native_api_backtests_without_history(runner, tmp_path):
    from fastapi.testclient import TestClient

    from tester.webapp.app import create_app
    from tester.webapp.store import RunStore

    store = RunStore(tmp_path / "runs")
    client = TestClient(create_app(store=store))
    st = client.get("/api/native/status").json()
    assert "orbnet" in st["strategies"] and st["pool"]["limit"] >= 1
    r = client.post("/api/native/backtests", json={
        "strategy": "orbnet", "pair": "NAS100/USD", "windows": [W1, W2], "fee": FEE,
        "points": [{"rrRatio": 1.0}, {"rrRatio": 2.0}], "trades": True})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["runs"] == 4 and [(x["point"], x["window"]) for x in out["results"]] == [(0, W1), (0, W2), (1, W1), (1, W2)]
    cfg, _ = load_profile("nas100_dukascopy_3m", strategy="orbnet", engine=engines.MULTICHARTS)
    want = summary_of(runner.run([json.dumps(type(cfg).from_dict({**cfg.to_dict(), "rrRatio": 2.0}).to_dict())], W2)[0],
                      INST, FEE, 10000)
    got = out["results"][3]["summary"]
    assert got == {k: v for k, v in want.items() if k not in ("exits", "streaks")}
    assert len(out["results"][3]["trades"]) == got["trades"]
    assert not list(store.all())                 # nič do histórie
    bad = client.post("/api/native/backtests", json={"strategy": "orb", "pair": "NAS100/USD"})
    assert bad.status_code == 422 and "C# jadro" in bad.text


def test_hyperopt_api_validates_native_only_options(tmp_path):
    from fastapi.testclient import TestClient

    from tester.webapp.app import create_app
    from tester.webapp.store import RunStore

    client = TestClient(create_app(store=RunStore(tmp_path / "runs")))
    base = {"params": {}, "strategy": "orbnet", "pair": "NAS100/USD", "timeframe": "3m",
            "timerange": W1, "space": {"rrRatio": "0.5:4:0.25"}, "epochs": 4}
    r = client.post("/api/hyperopts", json={**base, "engine": "multicharts", "objectives": ["drawdown"], "sampler": "cmaes"})
    assert r.status_code == 422 and "CMA-ES" in r.text
    r = client.post("/api/hyperopts", json={**base, "engine": "multicharts", "windows": ["2025-01-01"]})
    assert r.status_code == 422 and "YYYYMMDD" in r.text
    r = client.post("/api/hyperopts/neexistuje/continue", json={"epochs": 10})
    assert r.status_code == 404


def test_webapp_walkforward_and_multiwindow_jobs(runner, tmp_path, monkeypatch):
    from tester.webapp import runner as runner_mod
    from tester.webapp.store import RunStore, make_run_id

    monkeypatch.setattr("tester.webapp.command.TMP_PROFILES", tmp_path / "profiles")
    monkeypatch.setattr("tester.webapp.runner.TMP_PROFILES", tmp_path / "profiles")
    store = RunStore(tmp_path / "runs")
    br = runner_mod.BacktestRunner(store)
    zaradene = []
    monkeypatch.setattr(br, "submit", lambda params, settings, **kw: zaradene.append(settings))
    params = runner_mod.default_params("nas100_dukascopy_3m", strategy="orbnet", engine="multicharts")[0]
    zaklad = {"strategy": "orbnet", "pair": "NAS100/USD", "engine": "multicharts", "timeframe": "3m",
              "timerange": W2, "fee": FEE, "wallet": 10000.0, "timeframe_detail": "1m", "profile": "nas100_dukascopy_3m"}
    knobs = {"rrRatio": "0.5:4:0.25", "nyRangeMinutes": "5:60:5"}

    s1 = {**zaklad, "hyperopt": {"knobs": knobs, "goal": "break_even", "epochs": 8, "seed": 1, "verify": True,
                                 "native": True, "sampler": "tpe", "windows": [W1, W2], "aggregate": "min",
                                 "select": "plateau", "mode": "search", "jobs": 4}}
    job = runner_mod.Job(id=make_run_id(params, s1), params=params, settings=s1, note="okna", user="t")
    br._run(job)
    assert job.status == "done", job.error
    z = store.get(job.id)["settings"]["hyperopt"]
    assert z["windows"] == [W1, W2] and z["plateau_select"]["chosen"] == z["best"]["epoch"]
    assert [(s["timerange"], s["hyperopt_run"]["tuned"]) for s in zaradene[:2]] == [(W1, True), (W2, True)]
    assert not any(s["hyperopt_run"]["tuned"] for s in zaradene[2:])

    zaradene.clear()
    s2 = {**zaklad, "hyperopt": {"knobs": knobs, "goal": "break_even", "epochs": 4, "seed": 1, "verify": True,
                                 "native": True, "sampler": "random", "windows": [W1, W2, W3], "mode": "walkforward",
                                 "jobs": 4}}
    job2 = runner_mod.Job(id=make_run_id(params, s2), params=params, settings=s2, note="wf", user="t")
    br._run(job2)
    assert job2.status == "done", job2.error
    wf = store.get(job2.id)["settings"]["hyperopt"]["walk_forward"]
    assert len(wf["folds"]) == 2 and wf["verdict"].startswith("WALK-FORWARD")
    assert zaradene == []                       # walk-forward overenie nepúšťa, má ho v sebe
    assert len(store.extra(job2.id, "epochs.json")) == 8

    s3 = {**zaklad, "hyperopt": {**s1["hyperopt"], "epochs": 4, "select": "best", "continue_from": job.id}}
    job3 = runner_mod.Job(id=make_run_id(params, s3), params=params, settings=s3, note="dalej", user="t")
    br._run(job3)
    assert job3.status == "done", job3.error
    assert len(store.extra(job3.id, "epochs.json")) == 12


def test_hub_estimate_counts_windows_and_folds():
    from tester.hub import protocol as P

    z = {"knobs": {"rrRatio": "1:3:0.5"}, "epochs": 100, "verify": False}
    jedno = {"timerange": "20240904-20250904", "engine": "multicharts", "hyperopt": z}
    styri = {**jedno, "hyperopt": {**z, "windows": ["a", "b", "c", "d"]}}
    wf = {**jedno, "hyperopt": {**z, "mode": "walkforward"}}
    t1 = P.estimate_seconds(jedno, [], cores=8) - P.STARTUP_SECONDS
    assert P.estimate_seconds(styri, [], cores=8) - P.STARTUP_SECONDS == pytest.approx(4 * t1)
    assert P.estimate_seconds(wf, [], cores=8) - P.STARTUP_SECONDS == pytest.approx(4 * t1)


def test_loss_penalty_unchanged():
    plan = build_plan({"rrRatio": "1:3:0.5"}, strategy="orbnet", min_trades=200)
    assert loss_of({"trades": 100, "break_even_pct": 0.1, "max_drawdown_pct": 1}, plan, 365) == UNUSABLE + 100
