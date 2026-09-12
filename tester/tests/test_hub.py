"""Distribuované počítanie (tester.hub): kapacita, odhad času, hub, agent, prenos behov.

Freqtrade sa tu nespúšťa. Hub beží cez FastAPI TestClient, agent dostane falošný runner
(behy „dobehnú", keď test povie) a falošné HTTP, ktoré volá ten istý TestClient — takže
sa preverí celá cesta: zadanie → pridelenie v heartbeate → postup → zip → vyzdvihnutie
zadávateľom → ack, aj obojsmerné rušenie a výpadok agenta.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tester.hub import protocol as P
from tester.hub.config import AgentConfig, load_state
from tester.hub.server import HubState, NameTaken, NoCapacity
from tester.hub.transfer import pack_runs, unpack_runs
from tester.webapp.store import RunStore

BT = {"strategy": "ibs", "pair": "BTC/USDT:USDT", "timeframe": "3m",
      "timerange": "20250904-20260904", "timeframe_detail": "1m", "engine": "freqtrade"}
HO = {**BT, "hyperopt": {"knobs": {"rrRatio": "2:8:0.5"}, "epochs": 100, "verify": True}}


def _payload(settings=BT, **extra) -> dict[str, Any]:
    return {"params": {"rrRatio": 3.0}, "settings": settings, "note": "test", "user": "t", **extra}


def _rec(run_id: str, settings=BT, status="done", duration=30.0, **extra) -> dict[str, Any]:
    return {"id": run_id, "status": status, "settings": dict(settings), "params": {"rrRatio": 3.0},
            "note": "x", "result": {"duration_s": duration, "trades": 5}, **extra}


# --------------------------------------------------------------------------- #
# protocol
# --------------------------------------------------------------------------- #


def test_kind_and_cores():
    assert P.kind_of(BT) == "backtest" and P.kind_of(HO) == "hyperopt"
    assert P.cores_for(BT) == 1
    assert P.cores_for(HO) == P.ALL
    assert P.cores_for({**HO, "hyperopt": {**HO["hyperopt"], "jobs": 4}}) == 4
    assert P.cores_for({**BT, "ai": {"enabled": True}}) == P.ALL
    assert P.window_days("20250904-20260904") == 365
    assert P.window_days("zle") == 0


def test_estimate_from_history_and_fallback():
    S = P.STARTUP_SECONDS
    # bez histórie: rok s 1m detailom ~30 s, mesiac nie dvanástina (štart je konštanta)
    assert P.estimate_seconds(BT, []) == pytest.approx(30.0, rel=0.05)
    assert P.estimate_seconds({**BT, "timerange": "20250904-20251004"}, []) == pytest.approx(S + 30 * 20 / 365, rel=0.05)
    # z histórie: medián sekúnd na deň (bez štartu) — rok trval 73 s, takže 2 roky ~ 10 + 2×63
    hist = [_rec(f"20260901-00000{i}-aaaaaa", duration=73.0) for i in range(3)]
    dva_roky = {**BT, "timerange": "20240904-20260904"}
    assert P.estimate_seconds(dva_roky, hist) == pytest.approx(S + 2 * 63.0, rel=0.02)
    # hyperopt bez histórie hyperoptov: epocha = okno / jadrá (bez štartu), plus 5 overovacích behov
    odhad = P.estimate_seconds(HO, hist, cores=4)
    assert odhad == pytest.approx(S + 100 * 63.0 / 4 + 5 * 73.0, rel=0.02)
    # s históriou hyperoptov: sekundy na epochu
    hist_ho = hist + [_rec("20260902-000000-bbbbbb", settings={**HO, "hyperopt": {**HO["hyperopt"], "epochs_done": 50}},
                           duration=500.0)]
    assert P.estimate_seconds(HO, hist_ho) == pytest.approx(S + 100 * 10.0 + 5 * 73.0, rel=0.02)
    # bez overenia je len ladenie
    assert P.estimate_seconds({**HO, "hyperopt": {**HO["hyperopt"], "verify": False}}, hist_ho) == pytest.approx(S + 1000.0)


def test_progress_from_log_and_remaining():
    lines = ["2026-09-12 loading", "| 12/100 | 0.5 |", "| 13/100 | 0.4 |", "datum 2026/09"]
    assert P.progress_from_log(lines, 100) == pytest.approx(0.13)
    assert P.progress_from_log(lines, 200) is None
    assert P.progress_from_log([], 100) is None
    assert P.remaining_seconds(100, 20, None) == 80
    assert P.remaining_seconds(100, 20, 0.5) == 20     # postup hovorí viac než odhad
    assert P.remaining_seconds(100, 150, None) == 30   # po prekročení odhadu nie nula


def test_progress_from_results_file(tmp_path: Path):
    f = tmp_path / "x.fthypt"
    assert P.progress_from_results(f, 10) is None          # súbor ešte nie je
    f.write_text('{"a":1}\n{"a":2}\n\n{"a":3}\n', encoding="utf-8")
    assert P.progress_from_results(f, 10) == pytest.approx(0.3)
    assert P.progress_from_results(f, 2) == 1.0
    assert P.progress_from_results(f, None) is None
    assert P.progress_from_results(None, 10) is None


def test_capacity_rules():
    agent = {"name": "a", "cores": 8, "slots": 8, "accept": True, "online": True, "load": {}}
    assert P.fits(agent, 1, []) and P.fits(agent, P.ALL, [])
    beh = {"cores": 1, "eta_seconds": 100}
    assert P.fits(agent, 1, [beh]) and P.fits(agent, 7, [beh]) and not P.fits(agent, 8, [beh])
    assert not P.fits(agent, P.ALL, [beh])
    assert P.eta_free(agent, P.ALL, [beh]) == 100
    hyper = {"cores": P.ALL, "eta_seconds": 600}
    assert not P.fits(agent, 1, [hyper])
    assert P.eta_free(agent, 1, [hyper]) == 600
    # lokálna fronta testera zaberá sloty rovnako
    zatazeny = {**agent, "load": {"running": 7, "queued": 0, "eta_seconds": 50}}
    assert P.fits(zatazeny, 1, []) and not P.fits(zatazeny, 2, [])
    assert P.eta_free(zatazeny, 2, []) == 50
    assert P.eta_free({**agent, "accept": False}, 1, []) is None
    assert P.eta_free({**agent, "online": False}, 1, []) is None
    # tri behy po 1 jadre, chcem 2: po prvom dobehnutom je voľných 2 (5 slotov)
    maly = {**agent, "slots": 5}
    behy = [{"cores": 1, "eta_seconds": t} for t in (30, 10, 20)]
    behy += [{"cores": 1, "eta_seconds": 40}]
    assert P.eta_free(maly, 2, behy) == 10


# --------------------------------------------------------------------------- #
# transfer
# --------------------------------------------------------------------------- #


def test_pack_unpack_roundtrip(tmp_path: Path):
    src, dst = RunStore(tmp_path / "a"), RunStore(tmp_path / "b")
    src.save(_rec("20260901-000001-aaaaaa"), trades=[{"x": 1}], log="log")
    src.save_extra("20260901-000001-aaaaaa", "epochs.json", [{"epoch": 1}])
    src.save(_rec("20260901-000002-bbbbbb"))
    data = pack_runs(src.root, ["20260901-000001-aaaaaa", "20260901-000002-bbbbbb", "neexistuje"])
    ids = unpack_runs(data, dst.root)
    assert ids == ["20260901-000001-aaaaaa", "20260901-000002-bbbbbb"]
    assert dst.get("20260901-000001-aaaaaa")["result"]["duration_s"] == 30.0
    assert dst.trades("20260901-000001-aaaaaa") == [{"x": 1}]
    assert dst.extra("20260901-000001-aaaaaa", "epochs.json") == [{"epoch": 1}]
    assert dst.log("20260901-000001-aaaaaa") == "log"


def test_unpack_ignores_foreign_paths(tmp_path: Path):
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../../evil.txt", "x")
        z.writestr("nie-id/run.json", "{}")
        z.writestr("20260901-000001-aaaaaa/run.json", json.dumps(_rec("20260901-000001-aaaaaa")))
    assert unpack_runs(buf.getvalue(), tmp_path) == ["20260901-000001-aaaaaa"]
    assert not (tmp_path.parent / "evil.txt").exists()


# --------------------------------------------------------------------------- #
# hub (stav)
# --------------------------------------------------------------------------- #


class Clock:
    def __init__(self, t: float = 1_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def hub(tmp_path: Path):
    clock = Clock()
    return HubState(tmp_path / "hub", token="tajne", clock=clock), clock


def _reg(state: HubState, name="srv", cores=8, slots=8, accept=True, instance="i1"):
    return state.register(name, instance=instance, cores=cores, slots=slots, accept=accept)


def test_register_static_names(hub):
    state, _ = hub
    a = _reg(state)
    assert a["online"] and a["slots"] == 8
    # ten istý proces sa smie zaregistrovať znova (reštart spojenia)
    _reg(state, instance="i1")
    # iný proces s tým istým menom nie, kým prvý žije
    with pytest.raises(NameTaken):
        _reg(state, instance="i2")
    with pytest.raises(ValueError):
        _reg(state, name="  ")


def test_submit_assigns_or_refuses(hub):
    state, _ = hub
    with pytest.raises(NoCapacity) as exc:
        state.submit(kind="backtest", payload=_payload(), submitter="lap")
    assert exc.value.eta_start is None  # nikto online

    _reg(state)
    job = state.submit(kind="backtest", payload=_payload(), submitter="lap")
    assert job["status"] == "assigned" and job["agent"] == "srv" and job["cores"] == 1
    assert job["summary"]["pair"] == "BTC/USDT:USDT" and "payload" not in job
    # hyperopt chce celý stroj, na ktorom už niečo beží -> odmietnutie s odhadom
    with pytest.raises(NoCapacity) as exc:
        state.submit(kind="hyperopt", payload=_payload(HO), submitter="lap", estimate_seconds=100)
    assert exc.value.eta_start == pytest.approx(P.DEFAULT_ETA_SECONDS)  # o bežiacom nič nevieme
    # s frontou sa zaradí…
    q = state.submit(kind="hyperopt", payload=_payload(HO), submitter="lap", queue=True)
    assert q["status"] == "queued"
    # …ale nie, keď by čakanie presiahlo strop
    with pytest.raises(NoCapacity):
        state.submit(kind="hyperopt", payload=_payload(HO), submitter="lap", queue=True, max_wait_seconds=10)
    with pytest.raises(ValueError):
        state.submit(kind="foo", payload=_payload(), submitter="lap")


def test_heartbeat_delivers_progress_result_and_finished(hub):
    state, clock = hub
    _reg(state)
    job = state.submit(kind="backtest", payload=_payload(), submitter="lap")
    # pridelený výpočet príde v heartbeate počítajúceho agenta
    odp = state.heartbeat("srv", {"instance": "i1", "load": {}, "jobs": []})
    assert [j["id"] for j in odp["assign"]] == [job["id"]]
    assert odp["assign"][0]["payload"]["params"] == {"rrRatio": 3.0}
    # agent hlási postup -> running, ETA sa prenesie do kapacity
    odp = state.heartbeat("srv", {"jobs": [{"id": job["id"], "status": "running", "progress": 0.5,
                                            "eta_seconds": 40, "run_id": "20260901-000001-aaaaaa"}]})
    assert odp["assign"] == []
    j = state.job(job["id"])
    assert j["status"] == "running" and j["progress"] == 0.5 and j["run_id"] == "20260901-000001-aaaaaa"
    assert state.capacity(P.ALL)["eta_start_seconds"] == 40
    assert state.capacity(1)["free"] == ["srv"]
    # výsledok: zip + run_ids
    r = state.result(job["id"], b"PK-zip", status="done", run_ids=["20260901-000001-aaaaaa"], agent="srv")
    assert r["status"] == "done" and r["has_result"] and r["run_ids"] == ["20260901-000001-aaaaaa"]
    assert state.result_path(job["id"]).read_bytes() == b"PK-zip"
    # cudzí agent výsledok odovzdať nesmie
    with pytest.raises(PermissionError):
        state.result(job["id"], b"", status="done", agent="iny")
    # zadávateľ ho dostane vo svojom heartbeate, kým nepotvrdí
    _reg(state, name="lap", instance="i9")
    odp = state.heartbeat("lap", {"jobs": []})
    assert [j["id"] for j in odp["finished"]] == [job["id"]]
    state.ack(job["id"])
    assert not state.result_path(job["id"]).exists()
    assert state.heartbeat("lap", {"jobs": []})["finished"] == []


def test_cancel_from_submitter_reaches_computing_agent(hub):
    state, _ = hub
    _reg(state)
    _reg(state, name="lap", instance="i9", accept=False)
    job = state.submit(kind="backtest", payload=_payload(), submitter="lap")
    state.heartbeat("srv", {"jobs": [{"id": job["id"], "status": "running"}]})
    c = state.cancel(job["id"], by="lap")
    assert c["status"] == "cancelling"
    # počítajúci agent dostane rušenie v heartbeate…
    odp = state.heartbeat("srv", {"jobs": [{"id": job["id"], "status": "running"}]})
    assert odp["cancel"] == [job["id"]]
    # …a keď beh zabije, výpočet je zrušený a zadávateľ sa to dozvie
    state.result(job["id"], b"", status="failed", error="killed", agent="srv")
    assert state.job(job["id"])["status"] == "cancelled"
    fin = state.heartbeat("lap", {"jobs": []})["finished"]
    assert fin[0]["id"] == job["id"] and fin[0]["status"] == "cancelled" and "lap" in fin[0]["error"]
    # vo fronte sa ruší hneď
    state.heartbeat("srv", {"jobs": [], "load": {"running": 1}})
    q = state.submit(kind="hyperopt", payload=_payload(HO), submitter="lap", queue=True)
    assert state.job(q["id"])["status"] == "queued"
    assert state.cancel(q["id"])["status"] == "cancelled"


def test_offline_agent_requeues_or_fails(hub):
    state, clock = hub
    _reg(state)
    a = state.submit(kind="backtest", payload=_payload(), submitter="lap", queue=True)
    b = state.submit(kind="backtest", payload=_payload(), submitter="lap")
    state.heartbeat("srv", {"jobs": [{"id": a["id"], "status": "running"},
                                      {"id": b["id"], "status": "running"}]})
    clock.t += state.agent_timeout + 1
    cap = state.capacity(1)
    assert cap["online"] == 0
    assert state.job(a["id"])["status"] == "queued"      # frontu dovolil -> skúsi sa znova
    assert state.job(b["id"])["status"] == "failed"      # nedovolil -> chyba
    assert "odml" in state.job(b["id"])["error"]
    # keď sa agent vráti, čakajúci výpočet dostane znova
    odp = state.heartbeat("srv", {"jobs": []})
    assert [j["id"] for j in odp["assign"]] == [a["id"]]
    assert state.job(a["id"])["attempts"] == 2


def test_lost_running_job_after_missed_reports(hub):
    state, _ = hub
    _reg(state)
    job = state.submit(kind="backtest", payload=_payload(), submitter="lap")
    state.heartbeat("srv", {"jobs": [{"id": job["id"], "status": "running"}]})
    for _ in range(3):
        state.heartbeat("srv", {"jobs": []})
    assert state.job(job["id"])["status"] == "failed"


def test_exclusive_and_parallel_slots(hub):
    state, _ = hub
    _reg(state, slots=4)
    behy = [state.submit(kind="backtest", payload=_payload(), submitter="lap") for _ in range(4)]
    assert all(j["status"] == "assigned" for j in behy)
    with pytest.raises(NoCapacity):
        state.submit(kind="backtest", payload=_payload(), submitter="lap")
    for j in behy:
        state.result(j["id"], b"", status="done", agent="srv")
    h = state.submit(kind="hyperopt", payload=_payload(HO), submitter="lap")
    assert h["status"] == "assigned" and h["cores"] == P.ALL
    with pytest.raises(NoCapacity):  # vedľa hyperoptu nič
        state.submit(kind="backtest", payload=_payload(), submitter="lap")
    # rozloženie: druhý agent s väčšou rezervou dostane ďalší výpočet
    _reg(state, name="srv2", slots=2, instance="i2")
    j = state.submit(kind="backtest", payload=_payload(), submitter="lap")
    assert j["agent"] == "srv2"


def test_state_survives_restart(tmp_path: Path):
    clock = Clock()
    state = HubState(tmp_path / "hub", clock=clock)
    _reg(state)
    q = state.submit(kind="backtest", payload=_payload(), submitter="lap", queue=True)
    state.heartbeat("srv", {"jobs": [], "load": {"running": 8}})
    q2 = state.submit(kind="backtest", payload=_payload(), submitter="lap", queue=True)
    assert state.job(q2["id"])["status"] == "queued"
    znovu = HubState(tmp_path / "hub", clock=clock)
    assert znovu.job(q2["id"])["status"] == "queued"
    assert znovu.job(q["id"])["status"] == "assigned"
    assert not znovu.agents["srv"]["online"]  # kým sa neohlási
    assert znovu.job(q2["id"], with_payload=True)["payload"]["params"] == {"rrRatio": 3.0}


# --------------------------------------------------------------------------- #
# hub (API) + agent
# --------------------------------------------------------------------------- #


class FakeHttp:
    """`HubHttp` nad TestClientom — agent a klient nepoznajú rozdiel."""

    def __init__(self, client, token: str) -> None:
        self.c = client
        self.h = {"Authorization": f"Bearer {token}"}
        self.timeout = 30

    def _raise(self, r):
        from tester.hub.client import HubError, NoCapacityError

        if r.status_code >= 400:
            detail = r.json().get("detail") if "json" in r.headers.get("content-type", "") else r.text
            raise (NoCapacityError if r.status_code == 409 else HubError)(r.status_code, detail)

    def get(self, path):
        r = self.c.get(path, headers=self.h); self._raise(r); return r.json()

    def get_bytes(self, path):
        r = self.c.get(path, headers=self.h); self._raise(r); return r.content

    def post(self, path, body=None):
        r = self.c.post(path, json=body or {}, headers=self.h); self._raise(r); return r.json()

    def post_bytes(self, path, data):
        r = self.c.post(path, content=data, headers={**self.h, "Content-Type": "application/zip"})
        self._raise(r); return r.json()


@dataclass
class FakeJob:
    id: str
    params: dict
    settings: dict
    note: str = ""
    user: str = ""
    status: str = "queued"
    started: str | None = None
    log_lines: list = field(default_factory=list)
    cancel_requested: bool = False

    def public(self):
        return {"id": self.id, "status": self.status, "settings": self.settings, "started": self.started}


class FakeRunner:
    """Runner, ktorému test hovorí, kedy beh dobehne."""

    def __init__(self, store: RunStore) -> None:
        self.store = store
        self.jobs: dict[str, FakeJob] = {}
        self.n = 0

    def submit(self, params, settings, note="", user=""):
        self.n += 1
        if params.get("rrRatio") == "zle":
            raise ValueError("neplatny config")
        j = FakeJob(id=f"20260901-00000{self.n}-{'a' * 6}", params=params, settings=settings, note=note, user=user)
        self.jobs[j.id] = j
        return j

    def job(self, run_id):
        return self.jobs.get(run_id)

    def snapshot(self):
        return [j.public() for j in self.jobs.values() if j.status in ("queued", "running")]

    def cancel(self, run_id):
        j = self.jobs.get(run_id)
        if j:
            j.cancel_requested = True
            self.finish(run_id, "failed")
        return bool(j)

    def start_run(self, run_id, started="2026-09-12T10:00:00+00:00"):
        self.jobs[run_id].status, self.jobs[run_id].started = "running", started

    def finish(self, run_id, status="done"):
        j = self.jobs[run_id]
        j.status = status
        self.store.save({**_rec(run_id, settings=j.settings, status=status), "params": j.params,
                         "error": "zrusene" if status == "failed" else None})


@pytest.fixture
def hub_api(tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.hub.server import create_hub_app

    clock = Clock()
    state = HubState(tmp_path / "hub", token="tajne", clock=clock)
    return TestClient(create_hub_app(state)), state, clock


def test_api_requires_token(hub_api):
    c, state, _ = hub_api
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/status").status_code == 401
    assert c.get("/api/status", headers={"Authorization": "Bearer zle"}).status_code == 401
    assert c.get("/api/status", headers={"X-Hub-Token": "tajne"}).status_code == 200


def _agent(name, tmp_path, http, runner=None, accept=True, send=True, clock=None):
    from tester.hub.agent import HubAgent

    store = RunStore(tmp_path / name / "runs")
    cfg = AgentConfig(name=name, hub_url="http://hub", token="tajne", accept=accept, send=send, max_parallel=4)
    r = runner or FakeRunner(store)
    a = HubAgent(cfg, r, store, http=http, state_path=tmp_path / name / "state.json", clock=clock or Clock())
    return a, r, store


def test_agent_end_to_end(hub_api, tmp_path: Path):
    """Zadanie → pridelenie → postup → zip → vyzdvihnutie zadávateľom → ack."""
    from tester.hub.client import HubClient

    c, state, clock = hub_api
    http = FakeHttp(c, "tajne")
    srv, runner, srv_store = _agent("srv", tmp_path, http)
    lap, _, lap_store = _agent("lap", tmp_path, http, accept=False)
    srv.tick(); lap.tick()
    assert state.agents["srv"]["slots"] == srv.slots <= 4 and not state.agents["lap"]["accept"]

    # zadávateľ (CLI cez klienta) sa spýta a pošle
    client = HubClient(http, "lap")
    assert client.capacity(1)["free"] == ["srv"]
    job = client.submit("backtest", _payload(), estimate_seconds=30)
    lap.note_sent(job, "test")
    assert job["status"] == "assigned" and job["agent"] == "srv"
    assert load_state(tmp_path / "lap" / "state.json").sent[job["id"]]["kind"] == "backtest"

    # počítajúci agent si ho vezme do runnera
    srv.tick()
    assert len(runner.jobs) == 1
    run_id = next(iter(runner.jobs))
    assert srv.state.computing[job["id"]]["run_id"] == run_id
    assert load_state(tmp_path / "srv" / "state.json").computing[job["id"]]["run_id"] == run_id
    # druhý heartbeat ho nepridá znova
    srv.tick()
    assert len(runner.jobs) == 1

    # beží: hlási sa postup a zvyšok z odhadu
    runner.start_run(run_id, started="2026-09-12T10:00:00+00:00")
    from datetime import datetime, timezone
    srv.clock.t = datetime(2026, 9, 12, 10, 0, 10, tzinfo=timezone.utc).timestamp()  # 10 s po štarte
    srv.tick()
    j = state.job(job["id"])
    assert j["status"] == "running" and j["run_id"] == run_id and j["eta_seconds"] is not None
    assert j["elapsed_seconds"] == pytest.approx(10.0, abs=1.0)

    # dobehne: backtest sa odovzdá hneď prvým tickom (na overovacie behy čaká len hyperopt)
    runner.finish(run_id, "done")
    srv.tick()
    j = state.job(job["id"])
    assert j["status"] == "done" and j["has_result"] and j["run_ids"] == [run_id]
    assert job["id"] not in srv.state.computing

    # zadávateľ si výsledok vyzdvihne v heartbeate: beh je v jeho histórii, ack zmazal zip
    lap.tick()
    assert lap_store.get(run_id)["status"] == "done"
    assert lap.state.sent[job["id"]]["status"] == "done" and lap.state.sent[job["id"]]["run_ids"] == [run_id]
    assert state.job(job["id"])["collected"] and not state.result_path(job["id"]).exists()
    # klientove collect je idempotentné: zip už nie je, behy nájde lokálne
    assert client.collect(job["id"], lap_store.root) == [run_id]


def test_agent_hyperopt_waits_for_verification_runs(hub_api, tmp_path: Path):
    from tester.hub.client import HubClient

    c, state, _ = hub_api
    http = FakeHttp(c, "tajne")
    srv, runner, srv_store = _agent("srv", tmp_path, http)
    srv.tick()
    job = HubClient(http, "lap").submit("hyperopt", _payload(HO))
    assert job["cores"] == P.ALL
    srv.tick()
    run_id = next(iter(runner.jobs))
    runner.start_run(run_id)
    runner.jobs[run_id].log_lines += ["| 25/100 | ...", "| 50/100 | ..."]
    srv.tick()
    assert state.job(job["id"])["progress"] == pytest.approx(0.5)
    # hyperopt dobehol a zaradil overovací beh — kým ten žije, výsledok sa neodovzdá
    # a hub vidí postup pod 100 % so zvyškom podľa overovacieho behu
    runner.finish(run_id, "done")
    over = runner.submit({"rrRatio": 4.0}, {**BT, "hyperopt_run": {"id": run_id, "tuned": False}})
    for _ in range(3):
        srv.tick()
    j = state.job(job["id"])
    assert j["status"] == "running" and j["progress"] == pytest.approx(0.8) and j["eta_seconds"] > 0
    runner.finish(over.id, "done")
    srv.tick(); srv.tick()
    j = state.job(job["id"])
    assert j["status"] == "done" and sorted(j["run_ids"]) == sorted([run_id, over.id])
    # v zipe sú oba behy
    lap = RunStore(tmp_path / "lap-runs")
    assert sorted(unpack_runs(state.result_path(job["id"]).read_bytes(), lap.root)) == sorted([run_id, over.id])


def test_agent_cancel_and_bad_config(hub_api, tmp_path: Path):
    from tester.hub.client import HubClient

    c, state, _ = hub_api
    http = FakeHttp(c, "tajne")
    srv, runner, _ = _agent("srv", tmp_path, http)
    lap, _, _ = _agent("lap", tmp_path, http, accept=False)
    srv.tick(); lap.tick()
    client = HubClient(http, "lap")

    # zlý config: agent to nahlási ako zlyhaný výpočet, nie ako svoju chybu
    zly = client.submit("backtest", _payload(params={"rrRatio": "zle"}) | {"params": {"rrRatio": "zle"}})
    srv.tick()
    assert state.job(zly["id"])["status"] == "failed" and "neplatny" in state.job(zly["id"])["error"]

    # zrušenie zadávateľom: hub -> počítajúci agent zabije beh -> zadávateľ dostane cancelled
    job = client.submit("backtest", _payload())
    srv.tick()
    run_id = next(i for i, j in runner.jobs.items() if j.status != "failed")
    runner.start_run(run_id)
    srv.tick()
    client.cancel(job["id"])
    assert state.job(job["id"])["status"] == "cancelling"
    srv.tick()
    assert runner.jobs[run_id].cancel_requested
    srv.tick()
    assert state.job(job["id"])["status"] == "cancelled"
    lap.tick()
    assert lap.state.sent[job["id"]]["status"] == "cancelled"
    # aj zrušený beh príde zadávateľovi do histórie (nesie log, aby bolo vidno, kde skončil)
    assert lap.state.sent[job["id"]]["run_ids"] == [run_id]
    assert lap.store.get(run_id)["status"] == "failed"

    # rušenie niečoho, čo agent nepočíta (napr. po reštarte bez stavu) — povie to hneď
    job2 = client.submit("backtest", _payload())
    srv.tick()
    state.cancel(job2["id"], by="hub")
    del srv.state.computing[job2["id"]]
    srv.tick()
    assert state.job(job2["id"])["status"] == "cancelled"


def test_agent_reports_local_load_without_hub_jobs(hub_api, tmp_path: Path):
    """Čo si tester spustil sám, zaberá sloty; výpočty hubu sa nepočítajú dvakrát."""
    from tester.hub.client import HubClient

    c, state, _ = hub_api
    http = FakeHttp(c, "tajne")
    srv, runner, _ = _agent("srv", tmp_path, http)
    srv.tick()
    lokalny = runner.submit({"rrRatio": 2.0}, HO)  # lokálny hyperopt testera
    runner.start_run(lokalny.id)
    srv.tick()
    a = state.agents["srv"]
    assert a["load"]["running"] == 1 and a["load"]["exclusive"]
    assert state.capacity(1)["free"] == []
    with pytest.raises(Exception):
        HubClient(http, "lap").submit("backtest", _payload())
    runner.finish(lokalny.id)
    srv.tick()
    job = HubClient(http, "lap").submit("backtest", _payload())
    srv.tick()
    assert state.agents["srv"]["load"]["running"] == 0  # výpočet hubu nie je „lokálna záťaž"
    assert state.job(job["id"])["status"] in ("assigned", "running")


def test_hub_prefers_agent_with_requested_version(hub):
    state, clock = hub
    state.register("srv", instance="i1", cores=8, slots=8, accept=True, version="aaa111")
    state.register("srv2", instance="i2", cores=2, slots=2, accept=True, version="bbb222")
    # bez verzie: väčšia rezerva vyhráva
    assert state.submit(kind="backtest", payload=_payload(), submitter="lap")["agent"] == "srv"
    # s verziou: kto ju má, aj keď má menšiu rezervu
    j = state.submit(kind="backtest", payload=_payload(), submitter="lap", version="bbb222")
    assert j["agent"] == "srv2" and j["version"] == "bbb222"
    # heartbeat verziu aktualizuje (agent si pullol)
    state.heartbeat("srv", {"jobs": [], "version": "bbb222", "needs_restart": True})
    assert state.agents["srv"]["version"] == "bbb222"
    assert state.overview()["agents"][0]["needs_restart"] is True
    # výsledok nesie, na čom sa naozaj počítalo
    r = state.result(j["id"], b"", status="done", agent="srv2", version="bbb333")
    assert r["agent_version"] == "bbb333"


def test_bye_keeps_assigned_jobs_for_restart(hub):
    state, clock = hub
    _reg(state)
    job = state.submit(kind="backtest", payload=_payload(), submitter="lap")
    state.bye("srv")
    assert not state.agents["srv"]["online"]
    assert state.job(job["id"])["status"] == "assigned"      # nový proces si ho vezme
    # nový proces s iným `instance` sa smie zaregistrovať hneď a výpočet dostane
    _reg(state, instance="i2")
    assert [j["id"] for j in state.heartbeat("srv", {"jobs": []})["assign"]] == [job["id"]]
    # keď sa po `bye` nevráti, výpočet sa stratí ako pri výpadku
    job2 = state.submit(kind="backtest", payload=_payload(), submitter="lap")
    state.bye("srv")
    clock.t += state.agent_timeout + 1
    state.capacity(1)
    assert state.job(job2["id"])["status"] == "queued"        # bol len pridelený -> späť do fronty


def _fake_git(monkeypatch, have: set[str], pulls: list, brings: str | None = "bbb222"):
    from tester.hub import gitcode

    monkeypatch.setattr(gitcode, "version", lambda: max(have))
    monkeypatch.setattr(gitcode, "has_version", lambda commit: not commit or commit in have)

    def fake_pull():
        pulls.append(1)
        if brings:
            have.add(brings)
        return {"ok": True, "output": "Fast-forward"}

    monkeypatch.setattr(gitcode, "pull", fake_pull)


def test_agent_pulls_missing_version_when_idle(hub_api, tmp_path: Path, monkeypatch):
    from tester.hub.client import HubClient

    c, state, _ = hub_api
    http = FakeHttp(c, "tajne")
    have, pulls = {"aaa111"}, []
    _fake_git(monkeypatch, have, pulls)
    srv, runner, _ = _agent("srv", tmp_path, http)
    srv.tick()
    assert state.agents["srv"]["version"] == "aaa111"
    client = HubClient(http, "lap")

    # commit, ktorý agent má: bez pullu, beh nesie odkiaľ prišiel a na čom bežal
    j1 = client.submit("backtest", _payload(), version="aaa111")
    srv.tick()
    assert pulls == [] and len(runner.jobs) == 1
    run_id = next(iter(runner.jobs))
    hub_info = runner.jobs[run_id].settings["hub"]
    assert hub_info == {"job": j1["id"], "submitter": "lap", "version_requested": "aaa111",
                        "version": "aaa111", "agent": "srv"}

    # novší commit, kým niečo beží: čaká, nepulluje
    j2 = client.submit("backtest", _payload(), version="bbb222")
    srv.tick()
    assert pulls == [] and len(runner.jobs) == 1
    assert state.job(j2["id"])["status"] == "assigned"

    # prvý beh dobehol a odovzdal sa -> pull -> prijme, hlási novú verziu
    runner.finish(run_id)
    srv.tick()
    assert state.job(j1["id"])["status"] == "done" and state.job(j1["id"])["agent_version"] == "aaa111"
    srv.tick()
    assert pulls == [1] and len(runner.jobs) == 2
    assert srv.version == "bbb222" and srv.code_changed and not srv.needs_restart
    srv.tick()  # novú verziu hub vidí v ďalšom heartbeate
    assert state.agents["srv"]["version"] == "bbb222"

    # commit, ktorý pull nedonesie (nepushnutý): zlyhá s jasnou chybou
    for r in list(runner.jobs):
        if runner.jobs[r].status != "done":
            runner.finish(r)
    srv.tick()
    j3 = client.submit("backtest", _payload(), version="ccc333")
    srv.tick()
    j = state.job(j3["id"])
    assert j["status"] == "failed" and "ccc333" in j["error"] and "git pull" in j["error"]
    assert pulls == [1, 1]


def test_headless_agent_restarts_after_pull(hub_api, tmp_path: Path, monkeypatch):
    from tester.hub.client import HubClient

    c, state, _ = hub_api
    http = FakeHttp(c, "tajne")
    have, pulls = {"aaa111"}, []
    _fake_git(monkeypatch, have, pulls)
    srv, runner, _ = _agent("srv", tmp_path, http)
    srv.restart_on_pull = True
    srv.tick()
    job = HubClient(http, "lap").submit("backtest", _payload(), version="bbb222")
    srv.tick()
    # pull prebehol, ale výpočet si vezme až nový proces
    assert pulls == [1] and srv.needs_restart and len(runner.jobs) == 0
    assert state.job(job["id"])["status"] == "assigned"
    srv.bye()
    assert not state.agents["srv"]["online"]
    # "nový proces": iná inštancia, rovnaké meno a stav na disku
    novy, runner2, _ = _agent("srv", tmp_path, http)
    novy.tick()
    assert len(runner2.jobs) == 1 and pulls == [1]
    novy.tick()  # a hub sa o behu dozvie v ďalšom heartbeate
    assert state.job(job["id"])["status"] == "running"


def test_hub_accept_request_and_runtime_cap(hub):
    state, clock = hub
    _reg(state)
    # prepnutie z hubu: pokyn ide v heartbeate, kým agent nehlási to isté
    state.request_accept("srv", False)
    assert state.heartbeat("srv", {"jobs": [], "accept": True})["set_accept"] is False
    assert state.overview()["agents"][0]["accept_request"] is False
    odp = state.heartbeat("srv", {"jobs": [], "accept": False})
    assert odp["set_accept"] is None and "accept_request" not in state.agents["srv"]
    assert not state.agents["srv"]["accept"]
    with pytest.raises(KeyError):
        state.request_accept("nikto", True)
    # strop na čas: hub je poistka — o dva intervaly po strope výpočet zruší
    state.request_accept("srv", True)
    state.heartbeat("srv", {"jobs": [], "accept": True})
    job = state.submit(kind="backtest", payload=_payload(), submitter="lap", max_seconds=100)
    assert job["max_seconds"] == 100
    state.heartbeat("srv", {"jobs": [{"id": job["id"], "status": "running"}]})
    clock.t += 100 + state.agent_timeout          # ešte v tolerancii
    state.heartbeat("srv", {"jobs": [{"id": job["id"], "status": "running"}]})
    assert state.job(job["id"])["status"] == "running"
    clock.t += state.agent_timeout + 1
    odp = state.heartbeat("srv", {"jobs": [{"id": job["id"], "status": "running"}]})
    assert state.job(job["id"])["status"] == "cancelling" and odp["cancel"] == [job["id"]]
    state.result(job["id"], b"", status="failed", agent="srv")
    assert "strop" in state.job(job["id"])["error"]


def test_agent_accept_toggle_from_hub_config_and_api(hub_api, tmp_path: Path):
    from tester.hub import config as hub_config

    c, state, _ = hub_api
    http = FakeHttp(c, "tajne")
    cfg_path = tmp_path / "srv" / "agent.json"
    hub_config.save(AgentConfig(name="srv", hub_url="http://hub", token="tajne", accept=True), cfg_path)
    from tester.hub.agent import HubAgent

    store = RunStore(tmp_path / "srv" / "runs")
    srv = HubAgent(hub_config.load(cfg_path), FakeRunner(store), store, http=http,
                   state_path=tmp_path / "srv" / "state.json", config_path=cfg_path)
    srv.tick()
    assert state.agents["srv"]["accept"] is True

    # 1) prepnutie „z webapp": platí hneď, zapíše sa do configu, hub to vidí v heartbeate
    srv.set_accept(False)
    assert hub_config.load(cfg_path).accept is False
    srv.tick()
    assert state.agents["srv"]["accept"] is False

    # 2) zmena súboru (tester.hub setup --accept): agent ju prevezme pri ticku
    import os
    import time

    hub_config.save(AgentConfig(name="srv", hub_url="http://hub", token="tajne", accept=True), cfg_path)
    os.utime(cfg_path, (time.time() + 5, time.time() + 5))   # nech je mtime iný aj na rýchlom disku
    srv.tick()
    assert srv.cfg.accept is True and state.agents["srv"]["accept"] is True

    # 3) z hubu: `set_accept` v heartbeate, agent si to zapíše
    state.request_accept("srv", False)
    srv.tick()
    assert srv.cfg.accept is False and hub_config.load(cfg_path).accept is False
    srv.tick()
    assert "accept_request" not in state.agents["srv"]


def test_agent_kills_run_over_time_cap(hub_api, tmp_path: Path):
    from datetime import datetime, timezone

    from tester.hub.client import HubClient

    c, state, _ = hub_api
    http = FakeHttp(c, "tajne")
    srv, runner, _ = _agent("srv", tmp_path, http)
    srv.tick()
    job = HubClient(http, "lap").submit("backtest", _payload(), max_seconds=120)
    srv.tick()
    run_id = next(iter(runner.jobs))
    assert srv.state.computing[job["id"]]["max_seconds"] == 120
    runner.start_run(run_id, started="2026-09-12T10:00:00+00:00")
    srv.clock.t = datetime(2026, 9, 12, 10, 1, 0, tzinfo=timezone.utc).timestamp()   # 60 s: v limite
    srv.tick()
    assert runner.jobs[run_id].status == "running"
    srv.clock.t = datetime(2026, 9, 12, 10, 3, 0, tzinfo=timezone.utc).timestamp()   # 180 s: nad limitom
    srv.tick()
    assert runner.jobs[run_id].cancel_requested and srv.state.computing[job["id"]]["timed_out"]
    srv.tick()
    j = state.job(job["id"])
    assert j["status"] == "failed" and "strop 2 min" in j["error"]

    # bez zadaného stropu platí trojnásobok odhadu, najmenej 10 minút
    job2 = HubClient(http, "lap").submit("backtest", _payload())
    srv.tick()
    run2 = next(r for r in runner.jobs if r != run_id)
    runner.start_run(run2, started="2026-09-12T10:00:00+00:00")
    srv.tick()
    assert srv.state.computing[job2["id"]]["max_seconds"] >= 600


def test_compare_seeds():
    from tester import hyperopt as ho

    def det(seed, over, verdict, be=0.1):
        return {"id": f"h{seed}", "hyperopt": {"seed": seed, "epochs_done": 50}, "overrides": over,
                "verify": [{"tuned": True, "result": {"break_even_pct": be}}], "verdict": verdict}

    rovnake = ho.compare_seeds([det(1, {"rrRatio": 4.0}, "VITAZ PREZIL: x"),
                                det(2, {"rrRatio": 4.0}, "NEJASNE: y")])
    assert "ROVNAKE" in rovnake and "prezilo overenie na ostatnych oknach: 1 z 2" in rovnake
    rozne = ho.compare_seeds([det(1, {"rrRatio": 4.0}, ""), det(2, {"rrRatio": 5.0}, ""),
                              det(3, {"rrRatio": 4.0}, "")])
    assert "ROZNE: 2 roznych vitazov z 3 seedov (najcastejsi 2x)" in rozne
    assert "ZIADNY seed" in ho.compare_seeds([det(1, {}, "")])
    assert "ziadne" in ho.compare_seeds([])
    # veľkostné pole vo víťazovi sa vypíše hodnotou
    assert "minSl=0.3" in ho.compare_seeds([det(1, {"minSl": {"value": 0.3, "unit": "pct"}}, "")])


def test_webapp_hub_form_endpoints(monkeypatch, tmp_path: Path):
    """Beh a hyperopt z formulára idú na hub s tými istými `settings` ako lokálne."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tradebot.core import IBSConfig
    from tester.hub import client as client_mod, config as hub_config
    from tester.webapp import app as app_mod
    from tester.webapp.app import create_app
    from tester.webapp.runner import BacktestRunner

    poslane = []

    class FakeClient:
        name = "lap"

        def submit(self, kind, payload, **kw):
            poslane.append((kind, payload, kw))
            return {"id": f"j{len(poslane)}", "status": "queued", "agent": None, "created": "t"}

        def jobs(self, live=True, mine=False):
            return [{"id": "j1", "status": "queued" if live else "done"}]

    class FakeAgent:
        def __init__(self):
            self.accept = True
            self.noted = []

        def note_sent(self, job, note):
            self.noted.append((job["id"], note))

        def set_accept(self, v):
            self.accept = v

        def public(self):
            return {"name": "lap", "accept": self.accept}

    monkeypatch.setattr(hub_config, "load", lambda path=None: AgentConfig(name="lap", hub_url="http://hub", token="t"))
    monkeypatch.setattr(client_mod.HubClient, "from_config", classmethod(lambda cls, cfg: FakeClient()))
    monkeypatch.setattr(app_mod.engines, "available", lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])

    store = RunStore(tmp_path)
    app = create_app(store, BacktestRunner(store, command_builder=lambda *a: ["python", "-c", ""]))
    agent = FakeAgent()
    app.state.hub_agent = agent
    c = TestClient(app)

    base = {"params": IBSConfig().to_dict(), "pair": "BTC/USDT:USDT", "timerange": "20260801-20260901",
            "note": "z formulara", "user": "Jana"}
    r = c.post("/api/hub/runs", json={**base, "queue": False, "max_wait_minutes": 15, "max_runtime_minutes": 30})
    assert r.status_code == 200, r.text
    kind, payload, kw = poslane[-1]
    assert kind == "backtest" and payload["settings"]["pair"] == "BTC/USDT:USDT"
    assert payload["settings"]["engine"] == "freqtrade" and payload["settings"]["fee"] is not None
    assert payload["user"] == "Jana" and kw["queue"] is False
    assert kw["max_wait_seconds"] == 900 and kw["max_seconds"] == 1800 and kw["estimate_seconds"] > 0
    assert agent.noted == [("j1", "z formulara")]
    # rovnaká validácia ako lokálne
    assert c.post("/api/hub/runs", json={**base, "timerange": "zle"}).status_code == 422
    assert c.post("/api/hub/runs", json={**base, "params": {**base["params"], "rrRatio": 99}}).status_code == 422

    r = c.post("/api/hub/hyperopts", json={**base, "space": {"rrRatio": "2:6:1"}, "epochs": 20, "queue": True})
    assert r.status_code == 200, r.text
    kind, payload, kw = poslane[-1]
    assert kind == "hyperopt" and payload["settings"]["hyperopt"]["knobs"] == {"rrRatio": "2:6:1"}
    assert payload["settings"]["hyperopt"]["epochs"] == 20 and payload["note"].startswith("hyperopt rrRatio")
    assert c.post("/api/hub/hyperopts", json={**base, "space": {"nieco": "1,2"}}).status_code == 422

    # prepínač prijímania a zoznam výpočtov
    assert c.post("/api/hub/accept", json={"accept": False}).json()["accept"] is False
    assert agent.accept is False
    assert c.get("/api/hub/jobs?live=false").json()[0]["status"] == "done"
    app.state.hub_agent = None
    assert c.post("/api/hub/accept", json={"accept": True}).status_code == 404


# --------------------------------------------------------------------------- #
# tokeny per agent, identita v API, log udalostí
# --------------------------------------------------------------------------- #


def test_tokens_and_identity(tmp_path: Path):
    from tester.hub.server import ADMIN

    clock = Clock()
    state = HubState(tmp_path / "hub", token="hlavny", clock=clock)
    assert state.identity("hlavny") == ADMIN
    assert state.identity("zle") is None and state.identity(None) is None
    t = state.add_token("srv")
    assert len(t) > 20 and state.identity(t) == "srv"
    assert state.token_names()[0]["name"] == "srv" and state.token_names()[0]["token_hint"].endswith("…")
    # súbor prežije reštart a bežiaci hub ho číta znova, keď sa zmení (`token add --local`)
    znovu = HubState(tmp_path / "hub", token="hlavny", clock=clock)
    assert znovu.identity(t) == "srv"
    iny = HubState(tmp_path / "hub", token="hlavny", clock=clock)
    t2 = iny.add_token("srv2")
    assert znovu.identity(t2) == "srv2"
    assert znovu.remove_token("srv2") and znovu.identity(t2) is None
    assert not znovu.remove_token("srv2")
    with pytest.raises(ValueError):
        state.add_token(" ")
    # hub bez jediného tokenu (vývoj na localhoste) je otvorený
    assert HubState(tmp_path / "hub2", clock=clock).identity(None) == ADMIN


def test_api_identity_scopes_agent_actions(tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.hub.server import create_hub_app

    state = HubState(tmp_path / "hub", token="hlavny", clock=Clock())
    t_srv, t_lap = state.add_token("srv"), state.add_token("lap")
    c = TestClient(create_hub_app(state))
    H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
    reg = {"instance": "i1", "cores": 4, "slots": 4, "accept": True, "send": True}

    assert c.get("/api/status", headers=H("zle")).status_code == 401
    # agent sa smie zaregistrovať len pod svojím menom
    assert c.post("/api/agents/register", json={**reg, "name": "iny"}, headers=H(t_srv)).status_code == 403
    assert c.post("/api/agents/register", json={**reg, "name": "srv"}, headers=H(t_srv)).status_code == 200
    assert c.post("/api/agents/register", json={**reg, "name": "lap", "accept": False}, headers=H(t_lap)).status_code == 200
    assert c.post("/api/agents/srv/heartbeat", json={"jobs": []}, headers=H(t_lap)).status_code == 403
    assert c.post("/api/agents/srv/heartbeat", json={"jobs": []}, headers=H(t_srv)).status_code == 200
    # zadať smie len pod sebou; správca pod hocikým
    telo = {"kind": "backtest", "payload": _payload(), "submitter": "srv"}
    assert c.post("/api/jobs", json=telo, headers=H(t_lap)).status_code == 403
    job = c.post("/api/jobs", json={**telo, "submitter": "lap"}, headers=H(t_lap)).json()
    admin_job = c.post("/api/jobs", json={**telo, "submitter": "lap"}, headers=H("hlavny")).json()
    assert job["agent"] == "srv" and admin_job["status"] in ("assigned", "queued")
    # parametre behu vidí zadávateľ a počítajúci agent, nie tretí
    t_x = state.add_token("x")
    assert c.get(f"/api/jobs/{job['id']}?payload=true", headers=H(t_x)).status_code == 403
    assert c.get(f"/api/jobs/{job['id']}?payload=true", headers=H(t_srv)).status_code == 200
    assert c.get(f"/api/jobs/{job['id']}", headers=H(t_x)).status_code == 200
    # výsledok odovzdá len počítajúci agent (meno sa berie z tokenu)
    assert c.post(f"/api/jobs/{job['id']}/result?status=done&run_ids=a", content=b"zip",
                  headers={**H(t_lap), "Content-Type": "application/zip"}).status_code == 403
    r = c.post(f"/api/jobs/{job['id']}/result?status=done&run_ids=20260901-000001-aaaaaa", content=b"zip",
               headers={**H(t_srv), "Content-Type": "application/zip"})
    assert r.status_code == 200 and r.json()["agent_version"] is None
    # stiahnuť a potvrdiť smie zadávateľ, nie počítajúci agent ani tretí
    assert c.get(f"/api/jobs/{job['id']}/result", headers=H(t_srv)).status_code == 403
    assert c.get(f"/api/jobs/{job['id']}/result", headers=H(t_lap)).content == b"zip"
    assert c.post(f"/api/jobs/{job['id']}/ack", headers=H(t_x)).status_code == 403
    assert c.post(f"/api/jobs/{job['id']}/ack", headers=H(t_lap)).status_code == 200
    # rušiť smie zadávateľ alebo počítajúci agent; `by` je z tokenu
    assert c.post(f"/api/jobs/{admin_job['id']}/cancel", headers=H(t_x)).status_code == 403
    assert c.post(f"/api/jobs/{admin_job['id']}/cancel", headers=H(t_lap)).json()["cancelled_by"] == "lap"
    # správcovské veci: accept, tokeny
    assert c.post("/api/agents/srv/accept?value=false", headers=H(t_srv)).status_code == 403
    assert c.post("/api/agents/srv/accept?value=false", headers=H("hlavny")).status_code == 200
    assert c.get("/api/tokens", headers=H(t_srv)).status_code == 403
    novy = c.post("/api/tokens/srv3", headers=H("hlavny")).json()["token"]
    assert state.identity(novy) == "srv3"
    assert c.delete("/api/tokens/srv3", headers=H("hlavny")).status_code == 200
    assert c.delete("/api/tokens/srv3", headers=H("hlavny")).status_code == 404
    assert {t["name"] for t in c.get("/api/tokens", headers=H("hlavny")).json()} == {"srv", "lap", "x"}


def test_event_log(tmp_path: Path):
    clock = Clock()
    state = HubState(tmp_path / "hub", token="t", clock=clock)
    _reg(state)
    job = state.submit(kind="backtest", payload=_payload(), submitter="lap", version="abc")
    state.heartbeat("srv", {"jobs": [{"id": job["id"], "status": "running"}]})
    state.cancel(job["id"], by="lap")
    state.result(job["id"], b"", status="failed", agent="srv")
    state.request_accept("srv", False)
    clock.t += state.agent_timeout + 1
    state.capacity(1)
    druhy = [e["event"] for e in reversed(state.events(limit=100))]
    assert druhy == ["agent_online", "job_submitted", "job_assigned", "job_started", "job_cancel",
                     "job_finished", "accept_request", "agent_offline"]
    fin = state.events(event="job_finished")[0]
    assert fin["job"] == job["id"] and fin["status"] == "cancelled" and fin["agent"] == "srv"
    assert "lap" in fin["error"] and fin["submitter"] == "lap"
    sub = state.events(event="job_submitted")[0]
    assert sub["version"] == "abc" and sub["cores"] == 1 and sub["queue"] is False
    # filtre: podľa výpočtu a podľa agenta (ako agent, zadávateľ alebo pôvodca)
    assert {e["event"] for e in state.events(job=job["id"])} == {"job_submitted", "job_assigned", "job_started",
                                                                  "job_cancel", "job_finished"}
    assert "job_cancel" in {e["event"] for e in state.events(agent="lap")}
    assert state.events(limit=2)[0]["event"] == "agent_offline" and len(state.events(limit=2)) == 2
    # súbor prežije reštart hubu
    riadky = (tmp_path / "hub" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(riadky) == 8 and json.loads(riadky[0])["event"] == "agent_online"
    znovu = HubState(tmp_path / "hub", token="t", clock=clock)
    assert len(znovu.events(limit=100)) == 8


def test_gitcode_pull_can_be_disabled(monkeypatch):
    from tester.hub import gitcode

    monkeypatch.setenv("TRADEBOT_HUB_PULL", "off")
    assert not gitcode.pull_enabled()
    r = gitcode.pull()
    assert r["ok"] is False and "hostite" in r["output"]
    monkeypatch.setenv("TRADEBOT_HUB_PULL", "on")
    assert gitcode.pull_enabled()


def test_headless_agent_restarts_when_code_on_disk_changed(hub_api, tmp_path: Path, monkeypatch):
    """Kontajner: pull sa robí na hostiteľovi; agent zmenu kódu spozná a reštartuje sa."""
    from tester.hub import gitcode
    from tester.hub.client import HubClient

    c, state, _ = hub_api
    http = FakeHttp(c, "tajne")
    aktualna = {"v": "aaa111"}
    monkeypatch.setattr(gitcode, "version", lambda: aktualna["v"])
    monkeypatch.setattr(gitcode, "has_version", lambda commit: True)
    monkeypatch.setattr(gitcode, "pull", lambda: {"ok": False, "output": "vypnuty"})
    srv, runner, _ = _agent("srv", tmp_path, http)
    srv.restart_on_pull = True
    srv.tick()
    client = HubClient(http, "lap")
    job = client.submit("backtest", _payload(), version="aaa111")
    srv.tick()
    assert len(runner.jobs) == 1 and not srv.needs_restart
    run_id = next(iter(runner.jobs))
    aktualna["v"] = "bbb222"                      # na hostiteľovi prebehol git pull
    job2 = client.submit("backtest", _payload(), version="bbb222")
    srv.tick()
    assert not srv.needs_restart and len(runner.jobs) == 1   # kým niečo počíta, nie
    runner.finish(run_id)
    srv.tick()
    srv.tick()
    assert srv.needs_restart and len(runner.jobs) == 1       # výpočet si vezme až nový proces
    assert state.job(job2["id"])["status"] == "assigned"


# --------------------------------------------------------------------------- #
# runner: workery a exkluzivita
# --------------------------------------------------------------------------- #


def test_runner_exclusive_and_results_dir(tmp_path: Path):
    import sys

    from tester.webapp.runner import BacktestRunner, Job

    assert Job(id="x", params={}, settings=HO).exclusive
    assert not Job(id="x", params={}, settings=BT).exclusive
    store = RunStore(tmp_path)
    r = BacktestRunner(store, workers=3, command_builder=lambda py, *a: [py, "-c", "raise SystemExit(0)"])
    assert r.workers == 3
    a = Job(id="20260901-000001-aaaaaa", params={}, settings=BT, status="running")
    h = Job(id="20260901-000002-bbbbbb", params={}, settings=HO)
    r.jobs = {a.id: a, h.id: h}
    r.order = [a.id, h.id]
    assert not r._can_start(h)          # hyperopt čaká, kým beží backtest
    assert r._can_start(Job(id="c", params={}, settings=BT))
    a.status, h.status = "done", "running"
    assert not r._can_start(Job(id="c", params={}, settings=BT))  # a naopak
    assert r.load() == {"running": 1, "exclusive": True, "queued": 0, "workers": 3}
    # per-beh adresár výsledkov ide do príkazu
    h.status = "done"
    r.python = sys.executable
    job = r.submit({"rrRatio": 3.0}, {**BT, "engine": "freqtrade"} | {"pair": "BTC/USDT:USDT"})
    import time
    for _ in range(100):
        if job.status in ("done", "failed"):
            break
        time.sleep(0.1)
    assert job.status == "failed" and "--backtest-directory" in job.log_lines[0]
    assert job.id in job.log_lines[0]


# --------------------------------------------------------------------------- #
# CLI: mriežka na hub naraz
# --------------------------------------------------------------------------- #


def test_cli_prefetch_submits_grid_at_once(monkeypatch, tmp_path: Path):
    """`_remote_prefetch` zadá všetky body s frontou; `_execute` ich potom len vyzdvihne."""
    import argparse

    from tester.hub import client as client_mod, config as hub_config, gitcode
    from tester.webapp import cli, store as store_mod

    calls: dict[str, list] = {"submit": [], "wait": [], "collect": []}

    class FakeClient:
        name = "lap"

        def capacity(self, demand):
            return {"free": ["srv"], "online": 1, "queued": 0, "eta_start_seconds": 0}

        def submit(self, kind, payload, **kw):
            calls["submit"].append((payload["note"], kw["queue"], kw.get("version")))
            return {"id": f"j{len(calls['submit'])}", "status": "assigned", "agent": "srv", "created": "t"}

        def wait(self, job_id, on_tick=None):
            calls["wait"].append(job_id)
            return {"id": job_id, "status": "done", "run_id": f"20260901-00000{job_id[1]}-aaaaaa"}

        def collect(self, job_id, root):
            rid = f"20260901-00000{job_id[1]}-aaaaaa"
            RunStore(root).save(_rec(rid, note=f"beh {job_id}"))
            calls["collect"].append(job_id)
            return [rid]

    monkeypatch.setattr(store_mod, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(hub_config, "load", lambda path=None: AgentConfig(name="lap", hub_url="http://hub", token="t"))
    monkeypatch.setattr(hub_config, "load_state", lambda path=None: hub_config.AgentState())
    monkeypatch.setattr(hub_config, "save_state", lambda state, path=None: None)
    monkeypatch.setattr(client_mod.HubClient, "from_config", classmethod(lambda cls, cfg: FakeClient()))
    monkeypatch.setattr(cli, "_webapp_hub_ready", lambda url: False)
    monkeypatch.setattr(gitcode, "version", lambda: "abc123")
    monkeypatch.setattr(gitcode, "dirty_code", lambda: [])
    cli._REMOTE_BATCH.clear()

    args = argparse.Namespace(remote=True, queue=False, max_wait=None, cores=None, user="t",
                              url="http://127.0.0.1:9", no_wait=False)
    body = [({"rrRatio": float(v)}, dict(BT), f"bod {v}") for v in (2, 3, 4)]

    cli._remote_prefetch(args, body)
    assert [q for _, q, _ in calls["submit"]] == [True, True, True]      # mriežka čaká vždy
    assert {v for _, _, v in calls["submit"]} == {"abc123"}
    assert len(cli._REMOTE_BATCH) == 3

    recs = [cli._execute(args, p_, s_, n_, quiet=True) for p_, s_, n_ in body]
    assert len(calls["submit"]) == 3                                     # nič sa nezadalo druhýkrát
    assert calls["wait"] == ["j1", "j2", "j3"] and calls["collect"] == ["j1", "j2", "j3"]
    assert [r["note"] for r in recs] == ["beh j1", "beh j2", "beh j3"]
    assert cli._REMOTE_BATCH == {}

    # samostatný beh mimo mriežky sa zadá až teraz a bez fronty (podľa --queue)
    rec = cli._execute(args, {"rrRatio": 9.0}, dict(BT), "solo", quiet=True)
    assert len(calls["submit"]) == 4 and calls["submit"][-1][1] is False
    assert rec["status"] == "done"

    # bez --remote sa prefetch nedotkne hubu
    args.remote = False
    cli._remote_prefetch(args, body)
    assert len(calls["submit"]) == 4
