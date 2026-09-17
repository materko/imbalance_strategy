"""História behov v gite bez kresieb: graf na vyžiadanie, mriežky len ako výsledky, prune.

Rozhodnutie za tým: beh s kresbami mal ~1,5 MB, mriežky ich vyrobili tisíce a repozitár
narástol na 11 GB. Beh preto nesie celý config a výsledok, graf sa prepočíta, keď ho niekto
otvorí, a body mriežok/matíc/overení sú riadky v `tester/sweeps/`.
"""

from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

import pytest

from tradebot.core import IBSConfig
from tester.webapp.batches import BatchStore, batch_tag
from tester.webapp.store import CHART_FILE, PLAN_FILE, RunStore

T0 = 1_736_121_600_000  # 2025-01-06 00:00 UTC


def _record(run_id: str, **settings) -> dict:
    return {
        "id": run_id, "status": "done", "created": "2026-09-05T10:00:00+00:00",
        "finished": "2026-09-05T10:01:00+00:00", "user": "t", "note": "",
        "settings": {"strategy": "ibs", "pair": "BTC/USDT:USDT", "timeframe": "3m",
                     "timerange": "20250904-20260904", "fee": 0.0005, "wallet": 10000,
                     "engine": "freqtrade", "instrument": "btcusdt_binance", **settings},
        "params": IBSConfig().to_dict(),
        "result": {"trades": 40, "pnl_pct": 3.0, "pnl_abs": 300.0, "profit_factor": 1.2, "winrate": 45.0, "max_drawdown_pct": 5.0,
                   "break_even_pct": 0.12},
        "series": {"equity": [], "market": []},
    }


def _chart(path: Path, objects: list[dict]) -> Path:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"version": 1, "counts": {}, "objects": objects}, fh)
    return path


def _trade(signal_ms: int, short: bool = False) -> dict:
    return {"open_date": "2025-09-05T10:03:00+00:00", "close_date": "2025-09-05T11:00:00+00:00",
            "open_rate": 100.0, "close_rate": 102.0, "is_short": short, "profit_abs": 2.0,
            "enter_tag": f"tb:{signal_ms}", "exit_reason": "roi"}


# --------------------------------------------------------------------------- #
# beh bez kresieb v histórii
# --------------------------------------------------------------------------- #


def test_beh_sa_ulozi_bez_kresieb_a_plan_obchodov_ostane_pre_analytiku(tmp_path: Path):
    store = RunStore(tmp_path / "runs")
    objs = [{"t": "box", "k": "sl_box", "x1": T0, "y1": 100.0, "y2": 99.0},
            {"t": "box", "k": "tp_box", "x1": T0, "y1": 100.0, "y2": 102.0},
            {"t": "box", "k": "sl_box", "x1": T0 + 60_000, "y1": 5.0, "y2": 4.0},   # bez obchodu
            {"t": "box", "k": "sd_zone_post", "x1": 0, "x2": 10}]
    rid = "20260905-120000-aaaaaa"
    d = store.save(_record(rid), trades=[_trade(T0)], log="x", chart_path=_chart(tmp_path / "c.gz", objs))

    assert sorted(p.name for p in d.iterdir()) == ["log.txt", PLAN_FILE, "run.json", "trades.json"]
    assert not (d / CHART_FILE).exists()
    plan = json.loads((d / PLAN_FILE).read_text(encoding="utf-8"))["objects"]
    assert [(o["k"], o["x1"]) for o in plan] == [("sl_box", T0), ("tp_box", T0)]

    # cache grafov je lokálna: po jej zmazaní (klon z gitu) analytika dostane výťah plánu
    (store.chart_cache / f"{rid}.json.gz").unlink()
    assert not store.has_chart(rid) and store.drawings(rid) is None
    assert store.chart(rid)["plan_only"] is True

    from tester import analytics as an

    s_grafom = an.enrich([_trade(T0)], {"objects": objs}, "ibs")[0]
    s_planom = an.enrich([_trade(T0)], store.chart(rid), "ibs")[0]
    assert s_planom["_sl_pct"] == s_grafom["_sl_pct"] and s_planom["_rr_planned"] == s_grafom["_rr_planned"] == 2.0


def test_starsi_beh_s_chart_json_gz_ho_pouziva_dalej(tmp_path: Path):
    store = RunStore(tmp_path / "runs")
    rid = "20260905-120000-aaaaaa"
    d = store.save(_record(rid), trades=[], log="")
    _chart(d / CHART_FILE, [{"t": "box", "k": "x", "x1": 1}])
    assert store.has_chart(rid) and store.drawings(rid)["objects"][0]["k"] == "x"


# --------------------------------------------------------------------------- #
# body mriežky len ako výsledok
# --------------------------------------------------------------------------- #


def _runner(store):
    from tester.webapp.runner import BacktestRunner, Job

    return BacktestRunner(store, command_builder=lambda *a: ["python", "-c", ""]), Job


def test_bod_mriezky_ide_do_sweeps_nie_do_historie(tmp_path: Path):
    store = RunStore(tmp_path / "runs")
    runner, Job = _runner(store)
    base = _record("x")
    for i, rr in enumerate((3, 5)):
        tag = {"id": "20260905-120000-abcd", "values": {"rrRatio": rr}, "goal": "break_even",
               "signature": "x" * 5000, "per_year": True, "points": 2}
        job = Job(id=f"20260905-12000{i}-bbbbb{i}", params={**base["params"], "rrRatio": float(rr)},
                  settings={**base["settings"], "sweep": tag}, note=f"bod {rr}", user="t", status="done")
        runner._persist(job, ({**base["result"], "break_even_pct": 0.1 * rr}, [_trade(T0)], {"equity": []}),
                        10.0, chart_path=_chart(tmp_path / f"c{i}.gz", []))

    assert store.all() == []                                   # história ostala prázdna
    assert not list(store.chart_cache.glob("*")) if store.chart_cache.exists() else True
    subor = store.batches.path("sweep", "20260905-120000-abcd")
    data = json.loads(subor.read_text(encoding="utf-8"))
    assert len(data["points"]) == 2 and "signature" not in data["points"][0]["tag"]
    assert data["points"][1]["params"] == {"rrRatio": 5.0}     # len rozdiel oproti základu

    body = store.tagged("sweep", "20260905-120000-abcd")
    assert [b["params"]["rrRatio"] for b in body] == [3.0, 5.0]
    assert body[1]["settings"]["sweep"]["values"] == {"rrRatio": 5} and body[1]["batch"]["kind"] == "sweep"
    assert body[1]["settings"]["pair"] == "BTC/USDT:USDT"     # celý config pre prehratie
    assert store.find("20260905-120001-bbbbb1")["result"]["break_even_pct"] == pytest.approx(0.5)

    from tester import sweep as sweep_mod

    assert sweep_mod.rank(body)[0]["id"] == "20260905-120001-bbbbb1"


def test_overenie_hyperoptu_nesie_interval_vitaza_pre_okolie(tmp_path: Path):
    from tester import plateau as pl

    store = RunStore(tmp_path / "runs")
    runner, Job = _runner(store)
    rec = _record("x")
    obchody = [{**_trade(T0 + i), "profit_abs": (3.0 if i % 3 else -2.0),
                "close_rate": 103.0 if i % 3 else 98.0, "amount": 1.0} for i in range(40)]
    job = Job(id="20260905-120000-cccccc", params=rec["params"], status="done", note="", user="t",
              settings={**rec["settings"], "hyperopt_run": {"id": "20260905-110000-dddddd", "tuned": True}})
    runner._persist(job, (rec["result"], obchody, {}), 1.0)

    vitaz = store.tagged("hyperopt_run", "20260905-110000-dddddd")[0]
    lo, hi = pl.winner_ci(vitaz, None)
    assert lo is not None and hi is not None and lo <= hi
    assert (lo, hi) == pl.winner_ci(rec, obchody)             # ten istý interval ako z obchodov


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.webapp import app as app_mod
    from tester.webapp.runner import BacktestRunner

    store = RunStore(tmp_path / "runs")
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    monkeypatch.setattr(runner, "start", lambda: None)          # fronta stojí
    return TestClient(app_mod.create_app(store, runner)), store, runner


def test_mriezka_z_vysledkov_a_bod_sa_prehra_ako_obycajny_beh(app_client):
    c, store, runner = app_client
    rec = _record("20260905-120000-eeeeee")
    rec["settings"]["sweep"] = {"id": "s1", "values": {"rrRatio": 4}, "goal": "break_even"}
    rec["params"]["rrRatio"] = 4.0
    store.batches.add_point(rec)

    detail = c.get("/api/sweeps/s1").json()
    assert detail["done"] == 1 and detail["rows"][0]["in_history"] is False
    assert c.get("/api/sweeps").json()["sweeps"][0]["id"] == "s1"
    # CLI čaká na bod cez /api/runs/<id> — dostane výsledok, nie „live" navždy
    det = c.get("/api/runs/20260905-120000-eeeeee").json()
    assert det["live"] is False and det["batch"] == {"kind": "sweep", "id": "s1"}
    assert c.get("/api/runs").json()["total"] == 0

    job = c.post("/api/points/20260905-120000-eeeeee/replay", json={"user": "ja"}).json()
    zaradeny = runner.jobs[job["id"]]
    assert batch_tag(zaradeny.settings) is None                 # obyčajný beh, pôjde do histórie
    assert zaradeny.params["rrRatio"] == 4.0 and zaradeny.settings["timerange"] == "20250904-20260904"
    assert "sweep s1" in zaradeny.note
    assert c.post("/api/points/20990101-000000-ffffff/replay").status_code == 404


def test_cli_replay_spusti_bod_ako_beh(tmp_path: Path, monkeypatch, capsys):
    import tester.webapp.cli as cli
    import tester.webapp.store as store_mod

    monkeypatch.setattr(store_mod, "RUNS_DIR", tmp_path)
    store = RunStore(tmp_path)
    rec = _record("20260905-120000-eeeeee")
    rec["settings"]["matrix"] = {"id": "m1", "pair": "BTC/USDT:USDT", "timeframe": "3m"}
    store.batches.add_point(rec)
    videne = {}

    def fake_execute(args, params, settings, note, quiet=False):
        videne.update(params=params, settings=settings, note=note)
        return {**rec, "id": "20260905-130000-111111", "settings": settings}

    monkeypatch.setattr(cli, "_execute", fake_execute)
    monkeypatch.setattr(cli, "server_alive", lambda url: False)
    assert cli.main(["replay", "20260905-120000-eeeeee"]) == 0
    assert "matrix" not in videne["settings"] and "instrument" not in videne["settings"]
    assert "matrix m1" in videne["note"]


# --------------------------------------------------------------------------- #
# graf na vyžiadanie
# --------------------------------------------------------------------------- #


def test_prepocet_grafu_na_pozadi_a_cache(app_client, tmp_path: Path):
    from tester.webapp.replay import ChartReplayer

    c, store, _ = app_client
    rid = "20260905-120000-aaaaaa"
    store.save(_record(rid), trades=[_trade(T0)], log="")
    volania = []

    def launcher(st, run_id, job):
        volania.append(run_id)
        job.log_lines.append("počítam")
        st.put_chart(run_id, _chart(tmp_path / "r.gz", [{"t": "box", "k": "sd_zone_post", "x1": 1}]),
                     {"source": "replay", "match": False, "warning": "Prepočítaný graf nesedí s obchodmi behu"})

    replayer = ChartReplayer(store, launcher=launcher)
    c.app.state.replayer = replayer
    from tester.webapp import app as app_mod
    c2 = type(c)(app_mod.create_app(store, c.app.state.runner, replayer))

    assert c2.get(f"/api/runs/{rid}").json()["record"]["chart"]["state"] == "missing"
    assert c2.get(f"/api/runs/{rid}/chart").status_code == 409
    stav = c2.post(f"/api/runs/{rid}/chart").json()
    assert stav["state"] in ("queued", "running", "ready")
    for _ in range(100):
        if c2.get(f"/api/runs/{rid}/chart/status").json()["state"] == "ready":
            break
        time.sleep(0.05)
    graf = c2.get(f"/api/runs/{rid}/chart").json()
    assert graf["objects"][0]["k"] == "sd_zone_post"
    assert "nesedí" in graf["warning"]                         # graf je, ale s varovaním
    # cache: druhé otvorenie nič neprepočítava
    assert c2.post(f"/api/runs/{rid}/chart").json()["state"] == "ready"
    assert volania == [rid]


def test_kontrola_prepoctu_porovna_obchody_aj_signaly():
    from types import SimpleNamespace

    from tester.webapp.replay import _warning, check_signals, compare_trades

    a = [_trade(T0), _trade(T0 + 180_000, short=True)]
    assert compare_trades(a, [dict(x) for x in a])["match"] is True
    zle = compare_trades(a, [a[0]])
    assert zle["match"] is False and zle["matched"] == 1
    zle["incomplete"] = ["beh nemá zapísaný inštrument (starší záznam)"]
    assert "v behu 2, v prepočte 1" in _warning(zle) and "inštrument" in _warning(zle)

    rows = {T0: SimpleNamespace(enter_long=1, enter_short=0),
            T0 + 180_000: SimpleNamespace(enter_long=1, enter_short=0)}   # short signál chýba
    sig = check_signals(a, rows, "tb:")
    assert sig["signals_ok"] == 1 and sig["signals_missing"] == 1 and not sig["match"]
    assert "signál engine chýba pri 1 z 2" in _warning({**sig, "incomplete": []})


def test_prepocet_multicharts_behu_sedi_a_pri_zmene_obchodov_varuje(tmp_path: Path, monkeypatch):
    """Skutočný prepočet cez emulátor (malé dáta): kresby vzniknú, obchody sa porovnajú."""
    pd = pytest.importorskip("pandas")
    from tradebot.core.types import INSTRUMENTS
    from tester import engines
    from tester.webapp import replay, runner as runner_mod

    inst = INSTRUMENTS["nas100_dukascopy"]
    data = tmp_path / "data" / "tester"
    (data / inst.data_source / inst.market).mkdir(parents=True)
    n = 600
    pd.DataFrame({
        "date": [pd.Timestamp(T0 + i * 60_000, unit="ms", tz="UTC") for i in range(n)],
        "open": [100.0 + (i % 17) for i in range(n)], "high": [102.0 + (i % 17) for i in range(n)],
        "low": [99.0 + (i % 17) for i in range(n)], "close": [101.0 + (i % 17) for i in range(n)],
        "volume": [1.0] * n,
    }).to_feather(data / inst.data_source / inst.market / f"{inst.data_stem}-1m.feather")
    monkeypatch.setattr(engines, "TESTER_DATA", data)

    params = runner_mod.default_params("docs/profily_archiv/ibs/nas100_dukas_3m.json")[0]
    settings = {"strategy": "ibs", "pair": "NAS100/USD", "timeframe": "3m", "timerange": "20250106-20250107",
                "fee": 0.0, "wallet": 10000.0, "engine": "multicharts", "instrument": "nas100_dukascopy"}
    profil = runner_mod.write_profile("t", params, "nas100_dukascopy", "ibs", directory=tmp_path / "p")
    summary, rows, series, _ = runner_mod.run_multicharts(params, settings, profil, log=lambda s: None)

    store = RunStore(tmp_path / "runs")
    rid = "20260905-120000-aaaaaa"
    rec = {**_record(rid), "settings": settings, "params": runner_mod.effective_params(params), "result": summary}
    store.save(rec, trades=rows, log="")
    check = replay.compute(store, rid, log=lambda s: None)
    assert check["match"] is True and check["warning"] is None and store.has_chart(rid)
    assert store.drawings(rid)["pair"] == "NAS100/USD"

    # obchody behu sa „zmenili" (iný kód/dáta v čase behu) → graf áno, ale s varovaním
    (store.chart_cache / f"{rid}.json.gz").unlink()
    (store.root / rid / "trades.json").write_text(json.dumps(rows + [_trade(T0)]), encoding="utf-8")
    check = replay.compute(store, rid, log=lambda s: None)
    assert check["match"] is False and "nesedí" in check["warning"] and store.has_chart(rid)


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #


def test_gitignore_pusti_behy_a_mriezky_ale_nie_kresby():
    import subprocess

    from tradebot.core.paths import REPO

    def ignored(path: str) -> bool:
        return subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=REPO).returncode == 0

    assert not ignored("tester/runs/20260905-120000-aaaaaa/run.json")
    assert not ignored("tester/runs/20260905-120000-aaaaaa/trades.json")
    assert not ignored("tester/runs/20260905-120000-aaaaaa/plan.json")
    assert not ignored("tester/sweeps/sweep-20260905-120000-abcd.json")
    assert ignored("tester/runs/20260905-120000-aaaaaa/chart.json.gz")
    assert ignored("tester/runs/.charts/20260905-120000-aaaaaa.json.gz")


def test_push_berie_sweeps_a_zastavi_sa_na_ignorovanej_historii(monkeypatch):
    from tester.webapp import gitsync

    volania = []

    def fake_git(*args, check=False):
        volania.append(args)
        out = ""
        if args[:2] == ("ls-files", "--others"):
            out = ("tester/runs/a/chart.json.gz\ntester/runs/.charts/a.json.gz\n"
                   "tester/runs/b/run.json\ntester/sweeps/sweep-x.json")
        return type("P", (), {"args": ("git", *args), "stdout": out, "stderr": "", "returncode": 0})()

    monkeypatch.setattr(gitsync, "_git", fake_git)
    monkeypatch.setattr(gitsync, "_paths", lambda: ["tester/runs", "tester/sweeps", "tester/profiles"])
    assert gitsync.ignored_history() == ["tester/runs/b/run.json", "tester/sweeps/sweep-x.json"]
    r = gitsync.push()
    assert r["ok"] is False and "Push zrušený" in r["output"] and "tester/runs/b/run.json" in r["output"]
    assert not any(a[0] in ("add", "commit", "push") for a in volania)     # nič sa neposlalo

    assert gitsync._message(["?? tester/sweeps/sweep-x.json", "?? tester/runs/b/run.json",
                             " D tester/runs/a/chart.json.gz"]) == \
        "Pridaj 1 beh backtestu a 1 výsledok hľadania z webapp (odstránených súborov: 1)"


def test_push_adresare_zahrnaju_sweeps(tmp_path: Path, monkeypatch):
    from tester.webapp import gitsync

    for name in ("runs", "sweeps", "profiles", "analytics"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(gitsync, "REPO", tmp_path)
    monkeypatch.setattr(gitsync, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(gitsync, "SWEEPS_DIR", tmp_path / "sweeps")
    monkeypatch.setattr(gitsync, "PROFILES_DIR", tmp_path / "profiles")
    monkeypatch.setattr(gitsync, "ANALYTICS_DIR", tmp_path / "analytics")
    assert gitsync._paths() == ["runs", "sweeps", "profiles", "analytics"]


# --------------------------------------------------------------------------- #
# prune
# --------------------------------------------------------------------------- #


def test_prune_bez_apply_nic_nezmeni_a_s_apply_prevedie_body(tmp_path: Path):
    from tester.webapp import prune

    store = RunStore(tmp_path / "runs")
    obyc = "20260905-120000-aaaaaa"
    d = store.save(_record(obyc), trades=[_trade(T0)], log="")
    _chart(d / CHART_FILE, [{"t": "box", "k": "sl_box", "x1": T0, "y1": 100.0, "y2": 99.0}])
    for i, rr in enumerate((3, 5)):
        rec = _record(f"20260905-12010{i}-bbbbb{i}")
        rec["settings"]["sweep"] = {"id": "s1", "values": {"rrRatio": rr}, "goal": "break_even"}
        rec["params"]["rrRatio"] = float(rr)
        dd = store.save(rec, trades=[_trade(T0)], log="")
        _chart(dd / CHART_FILE, [])

    pred = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    plan = prune.plan(store)
    text = prune.report(plan)
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")) == pred   # suchý beh
    assert len(plan.charts) == 1 and plan.plans_to_extract == 1 and plan.child_runs == 2
    assert "sweep" in text and "2 behov" in text

    out = prune.apply(store, plan, log=lambda s: None)
    assert out == {"batches": 1, "plans": 1, "charts": 1, "child_runs": 2}
    assert [r["id"] for r in store.all()] == [obyc]
    assert not (d / CHART_FILE).exists() and (d / PLAN_FILE).exists()
    assert store.chart(obyc)["plan_only"] is True
    assert [b["params"]["rrRatio"] for b in store.tagged("sweep", "s1")] == [3.0, 5.0]
