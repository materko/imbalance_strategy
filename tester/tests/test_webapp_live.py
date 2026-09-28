"""Karta Live vo webapp (docs/LIVE.md): API nad zrkadlom a zrkadlo samo.

Zrkadlo (`LiveMirror`) sa testuje bez vlákna a bez siete — hub je falošný objekt s `get()`,
lokálny spool falošný reader s `read()`/`commit()`. Stránka číta len zrkadlo, takže API
stačí naplniť `LiveStore` v dočasnom adresári.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tradebot.live.store import LiveStore


def _hello(session: str = "a1b2c3d4", seq: int = 1, t: int = 1_790_000_000_000) -> dict:
    return {"seq": seq, "t": t, "k": "hello", "schema": 1, "platform": "mt5", "account": "5012345-Demo",
            "symbol": "NAS100", "tf": 3, "strategy": "ibsnet", "profile": "nas100_dukas_3m", "session": session,
            "host": "VM-TRADE-01", "tester": False, "config": {}, "instrument": {}}


def _events(session: str = "a1b2c3d4") -> list[dict]:
    t0 = 1_790_000_000_000
    return [
        _hello(session, 1, t0),
        {"seq": 2, "t": t0 + 1, "k": "bar", "bt": t0 - 180_000, "o": 20100.5, "h": 20110.0, "l": 20099.0,
         "c": 20105.25, "v": 1234, "ready": True, "mb": 1},
        {"seq": 3, "t": t0 + 2, "k": "order", "bt": t0 - 180_000, "ready": True, "a": "entry", "id": "L-4711",
         "src": 4711, "dir": 1, "ot": "limit", "r": "zone touch",
         "p": {"dir": 1, "e": 20090.0, "sl": 20070.0, "tp": 20150.0, "q": 1, "sd": 20}},
        {"seq": 4, "t": t0 + 3, "k": "draw", "bt": t0 - 180_000,
         "d": [{"t": "box", "k": "zone", "id": "z4711", "x1": t0 - 360_000, "y1": 20095.0, "x2": t0 - 180_000,
                "y2": 20085.0, "bc": "#089981", "fc": "#08998133"}]},
        {"seq": 5, "t": t0 + 60_000, "k": "fill", "ft": t0 + 59_800, "id": "L-4711", "side": "in", "exit": "",
         "price": 20090.0, "qty": 1, "ready": True},
    ]


INSTANCE = "mt5_5012345-Demo_NAS100_3m_ibsnet"


@pytest.fixture
def live_app(tmp_path: Path, monkeypatch):
    """Webapp s prázdnym zrkadlom v dočasnom adresári; vlákno zrkadla sa nespúšťa."""
    fastapi = pytest.importorskip("fastapi")  # noqa: F841
    from fastapi.testclient import TestClient

    from tester.webapp.api import live as live_mod
    from tester.webapp.app import create_app
    from tester.webapp.runner import BacktestRunner
    from tester.webapp.store import RunStore

    monkeypatch.setattr(live_mod, "LIVE_MIRROR", tmp_path / "live" / "mirror.sqlite")
    monkeypatch.setattr(live_mod, "LIVE_MIRROR_CURSOR", tmp_path / "live" / "mirror_cursor.json")
    monkeypatch.setattr(live_mod, "LIVE_CURSOR_WEBAPP", tmp_path / "live" / "cursor_webapp.json")
    store = RunStore(tmp_path / "runs")
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    app = create_app(store, runner)
    return TestClient(app), app.state.live_mirror


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #


def test_api_prazdne_zrkadlo(live_app):
    c, mirror = live_app
    r = c.get("/api/live")
    assert r.status_code == 200
    body = r.json()
    assert body["instances"] == []
    assert body["mirror"]["running"] is False and body["mirror"]["hub_cursor"] == 0
    assert set(body["mirror"]) >= {"hub_url", "hub_cursor", "last_ok", "last_error", "local_roots"}
    assert c.get("/api/live/neexistuje/snapshot").status_code == 404
    assert c.get("/api/live/neexistuje/events").json() == []


def test_api_instancia_a_snapshot(live_app):
    c, mirror = live_app
    # do zrkadla z iného „procesu" — ten istý súbor, vlastný LiveStore (sqlite WAL)
    LiveStore(mirror.mirror_path).ingest("agent-x", INSTANCE, "a1b2c3d4", _events())

    body = c.get("/api/live").json()
    assert [i["id"] for i in body["instances"]] == [INSTANCE]
    inst = body["instances"][0]
    assert inst["platform"] == "mt5" and inst["symbol"] == "NAS100" and inst["tf"] == 3
    assert inst["strategy"] == "ibsnet" and inst["agent"] == "agent-x" and inst["last_bar_ms"] == 1_790_000_000_000 - 180_000

    snap = c.get(f"/api/live/{INSTANCE}/snapshot?bars=100").json()
    assert snap["instance"]["id"] == INSTANCE
    assert [b["c"] for b in snap["bars"]] == [20105.25]
    assert snap["draw"][0]["d"][0]["id"] == "z4711"
    assert [f["id"] for f in snap["fills"]] == ["L-4711"]
    assert [o["a"] for o in snap["orders"]] == ["entry"]

    rows = c.get(f"/api/live/{INSTANCE}/events?kinds=bar,fill&limit=10").json()
    assert [r["event"]["k"] for r in rows] == ["bar", "fill"]
    dalsie = c.get(f"/api/live/{INSTANCE}/events?after={rows[0]['id']}").json()
    assert [r["event"]["k"] for r in dalsie] == ["order", "draw", "fill"]


def _bye(seq: int, t: int, reason: str = "terminated") -> dict:
    return {"seq": seq, "t": t, "k": "bye", "reason": reason}


def _second_session(t0: int = 1_790_000_000_000 + 600_000) -> list[dict]:
    """Nový štart stratégie o 10 min neskôr: iný profil, dva bary, jeden posun SL/TP, bez `bye`."""
    h = _hello("ffffffff", 1, t0)
    h["profile"] = "nas100_v2"
    return [
        h,
        {"seq": 2, "t": t0 + 1, "k": "bar", "bt": t0 - 180_000, "o": 20110.0, "h": 20120.0, "l": 20105.0,
         "c": 20115.0, "v": 900, "ready": True, "mb": 1},
        {"seq": 3, "t": t0 + 2, "k": "order", "bt": t0 - 180_000, "ready": True, "a": "modify", "id": "L-4711",
         "r": "trail", "p": {"sl": 20080.0, "tp": 20150.0}},
        {"seq": 4, "t": t0 + 180_001, "k": "bar", "bt": t0, "o": 20115.0, "h": 20125.0, "l": 20110.0,
         "c": 20120.0, "v": 800, "ready": True, "mb": 1},
    ]


def test_api_behy_a_snapshot_so_session(live_app):
    """Dva behy jednej inštancie v zrkadle: `/sessions` ich vymenuje (najnovší prvý, živý bez `bye`),
    snapshot/events so `session=` dajú len ten beh; bez `session` ako doteraz naprieč behmi."""
    c, mirror = live_app
    t0 = 1_790_000_000_000
    st = LiveStore(mirror.mirror_path)
    st.ingest("agent-x", INSTANCE, "a1b2c3d4", _events() + [_bye(6, t0 + 120_000)])
    st.ingest("agent-x", INSTANCE, "ffffffff", _second_session(t0 + 600_000))
    mirror.clock = lambda: (t0 + 600_000 + 240_000) / 1000.0

    assert c.get("/api/live/neexistuje/sessions").status_code == 404
    behy = c.get(f"/api/live/{INSTANCE}/sessions").json()
    assert [b["session"] for b in behy] == ["ffffffff", "a1b2c3d4"]
    assert behy[1]["ended"] == t0 + 120_000 and behy[1]["reason"] == "terminated" and behy[1]["live"] is False
    assert behy[1]["bars"] == 1 and behy[1]["fills"] == 1 and behy[1]["orders"] == 1 and behy[1]["profile"] == "nas100_dukas_3m"
    assert behy[0]["started"] == t0 + 600_000 and behy[0]["ended"] is None and behy[0]["profile"] == "nas100_v2"
    assert behy[0]["bars"] == 2 and behy[0]["orders"] == 1 and behy[0]["fills"] == 0 and behy[0]["agent"] == "agent-x"
    # hodiny zrkadla: 4 min po štarte behu 2, posledný bar pred 1 min → do 3 barov TF = živý
    assert behy[0]["live"] is True

    a = c.get(f"/api/live/{INSTANCE}/snapshot?session=a1b2c3d4").json()
    assert a["session"] == "a1b2c3d4" and [b["c"] for b in a["bars"]] == [20105.25]
    assert [o["a"] for o in a["orders"]] == ["entry"] and [n["k"] for n in a["notes"]] == ["bye"]
    b = c.get(f"/api/live/{INSTANCE}/snapshot?session=ffffffff").json()
    assert [x["c"] for x in b["bars"]] == [20115.0, 20120.0] and [o["a"] for o in b["orders"]] == ["modify"]
    assert b["fills"] == [] and b["notes"] == []
    assert len(c.get(f"/api/live/{INSTANCE}/snapshot?session=ffffffff&bars=1").json()["bars"]) == 1
    vsetko = c.get(f"/api/live/{INSTANCE}/snapshot").json()
    assert vsetko["session"] is None and len(vsetko["bars"]) == 3
    assert c.get(f"/api/live/{INSTANCE}/snapshot?bars=9999").status_code == 422

    rows = c.get(f"/api/live/{INSTANCE}/events?session=ffffffff&kinds=order").json()
    assert [r["event"]["a"] for r in rows] == ["modify"] and rows[0]["session"] == "ffffffff"
    assert len(c.get(f"/api/live/{INSTANCE}/events?kinds=bar").json()) == 3


# --------------------------------------------------------------------------- #
# zrkadlo: hub
# --------------------------------------------------------------------------- #


class _FakeHubHttp:
    """`GET /api/live/export?after=&limit=` nad zoznamom riadkov; počíta volania."""

    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[str] = []

    def get(self, path: str):
        self.calls.append(path)
        q = dict(p.split("=") for p in path.split("?", 1)[1].split("&"))
        after, limit = int(q["after"]), int(q["limit"])
        return [r for r in self.rows if r["id"] > after][:limit]


def _export_rows(events: list[dict], *, agent: str = "trade-pc", start_id: int = 1,
                 session: str = "a1b2c3d4") -> list[dict]:
    return [{"id": start_id + i, "agent": agent, "instance": INSTANCE, "session": session, "event": ev}
            for i, ev in enumerate(events)]


def _mirror(tmp_path: Path, hub=None, reader=None, **kw):
    from tester.webapp.api.live import LiveMirror

    return LiveMirror(tmp_path / "mirror.sqlite", tmp_path / "mirror_cursor.json",
                      local_cursor=tmp_path / "cursor_webapp.json",
                      hub_factory=lambda: hub, reader_factory=lambda p: reader, **kw)


def test_zrkadlo_stiahne_z_hubu_po_strankach_a_posunie_kurzor(tmp_path: Path):
    http = _FakeHubHttp(_export_rows(_events()))
    cfg = SimpleNamespace(name="notebook", hub_url="http://hub.test:8790", send=True)
    m = _mirror(tmp_path, hub=(cfg, http), clock=lambda: 123.0)

    m.tick()
    # 5 riadkov < limit → jedna stránka; kurzor = najvyšší rowid hubu
    assert m.hub_cursor == 5 and m.last_error is None and m.last_ok == 123.0
    assert [i["id"] for i in m.store.instances()] == [INSTANCE]
    assert m.store.instances()[0]["agent"] == "trade-pc"
    assert (tmp_path / "mirror_cursor.json").exists()

    # druhá otočka: nič nové, kurzor stojí, nič sa nezdvojí
    m.tick()
    assert m.hub_cursor == 5 and m.store.cursor() == 5
    assert http.calls[-1] == "/api/live/export?after=5&limit=5000"


def test_zrkadlo_prenesie_dva_behy_jednej_instancie(tmp_path: Path):
    """Reštart stratégie na obchodnom PC = druhá session tej istej inštancie; zrkadlo ju zoskupí
    zvlášť (kľúč (agent, inštancia, session)) a `sessions()` zrkadla dá obe ako hub."""
    t0 = 1_790_000_000_000
    stary = _events() + [_bye(6, t0 + 120_000)]
    rows = _export_rows(stary) + _export_rows(_second_session(t0 + 600_000), start_id=len(stary) + 1, session="ffffffff")
    http = _FakeHubHttp(rows)
    cfg = SimpleNamespace(name="notebook", hub_url="http://hub.test:8790", send=True)
    m = _mirror(tmp_path, hub=(cfg, http), clock=lambda: (t0 + 600_000 + 240_000) / 1000.0)

    assert m.pull_hub(http, limit=3) == len(rows)        # stránka pretne hranicu behov — nevadí
    behy = m.store.sessions(INSTANCE)
    assert [(b["session"], b["bars"], b["live"]) for b in behy] == [("ffffffff", 2, True), ("a1b2c3d4", 1, False)]
    assert behy[1]["reason"] == "terminated" and behy[0]["profile"] == "nas100_v2"
    assert m.store.instance(INSTANCE)["last_session"] == "ffffffff"
    assert {r["session"] for r in m.store.events(INSTANCE)} == {"a1b2c3d4", "ffffffff"}
    assert [o["a"] for o in m.store.snapshot(INSTANCE, session="ffffffff")["orders"]] == ["modify"]
    # opakovaný export od nuly nič nezdvojí ani v jednom behu
    m.hub_cursor = 0
    assert m.pull_hub(http) == 0
    assert [b["bars"] for b in m.store.sessions(INSTANCE)] == [2, 1]


def test_zrkadlo_stranky_po_limite_a_opakovane_riadky(tmp_path: Path):
    """Dve stránky (limit 2 → 2 + 2 + 1) a potom hub pošle časť znova — nič dvakrát."""
    rows = _export_rows(_events())
    http = _FakeHubHttp(rows)
    cfg = SimpleNamespace(name="notebook", hub_url="http://hub.test:8790", send=True)
    m = _mirror(tmp_path, hub=(cfg, http))

    assert m.pull_hub(http, limit=2) == 5
    assert m.hub_cursor == 5
    assert [p.split("after=")[1].split("&")[0] for p in http.calls] == ["0", "2", "4"]

    # kurzor „zabudnutý" (napr. súbor zmazaný) → hub pošle všetko znova, store ignoruje duplikáty
    m.hub_cursor = 0
    assert m.pull_hub(http, limit=2) == 0
    assert m.store.cursor() == 5 and len(m.store.events(INSTANCE)) == 5


def test_zrkadlo_kurzor_prezije_restart_a_ina_adresa_hubu_zacina_od_nuly(tmp_path: Path):
    from tester.webapp.api.live import LiveMirror

    http = _FakeHubHttp(_export_rows(_events()))
    cfg = SimpleNamespace(name="notebook", hub_url="http://hub.test:8790", send=True)
    _mirror(tmp_path, hub=(cfg, http)).tick()

    znova = _mirror(tmp_path, hub=(cfg, http))
    znova.tick()
    assert znova.hub_cursor == 5 and http.calls[-1].startswith("/api/live/export?after=5")

    iny = SimpleNamespace(name="notebook", hub_url="http://iny.test:8790", send=True)
    m2 = LiveMirror(tmp_path / "mirror.sqlite", tmp_path / "mirror_cursor.json",
                    local_cursor=tmp_path / "c.json", hub_factory=lambda: (iny, http), reader_factory=lambda p: None)
    m2.tick()
    assert http.calls[-1].startswith("/api/live/export?after=0")


def test_zrkadlo_chyba_hubu_sa_zapise_a_dalsi_tik_ide_znova(tmp_path: Path):
    class Padajuci:
        def __init__(self) -> None:
            self.n = 0

        def get(self, path):
            self.n += 1
            if self.n == 1:
                raise OSError("connection refused")
            return []

    cfg = SimpleNamespace(name="notebook", hub_url="http://hub.test:8790", send=True)
    m = _mirror(tmp_path, hub=(cfg, Padajuci()))
    m.tick()
    assert m.last_error and "connection refused" in m.last_error and m.last_ok is None
    m.tick()
    assert m.last_error is None and m.last_ok is not None


# --------------------------------------------------------------------------- #
# zrkadlo: lokálny spool
# --------------------------------------------------------------------------- #


class _FakeReader:
    """Dávky ako `tradebot.live.spool.SpoolReader`: `read()` vráti, čo je za kurzorom, `commit()` posunie."""

    def __init__(self, batches: list) -> None:
        self.pending = list(batches)
        self.committed: list = []
        self.roots = [Path("C:/spool")]

    def read(self, max_events: int = 500):
        return [b for b in self.pending if b not in self.committed][:1]

    def commit(self, batch) -> None:
        self.committed.append(batch)


def test_zrkadlo_cita_lokalny_spool_a_potvrdi_davku(tmp_path: Path):
    evs = _events()
    batches = [SimpleNamespace(instance=INSTANCE, session="a1b2c3d4", events=evs[:3], path=None),
               SimpleNamespace(instance=INSTANCE, session="a1b2c3d4", events=evs[3:], path=None)]
    reader = _FakeReader(batches)
    m = _mirror(tmp_path, hub=None, reader=reader)

    m.tick()
    assert reader.committed == batches
    assert m.local_roots == [str(Path("C:/spool"))]
    assert m.local_agent == "local" and m.hub_url is None
    inst = m.store.instances()
    assert [i["id"] for i in inst] == [INSTANCE] and inst[0]["agent"] == "local"
    assert len(m.store.events(INSTANCE)) == 5

    # bez hubu je stav v poriadku; ďalší tik bez dávok nič nemení
    assert m.last_error is None
    m.tick()
    assert len(m.store.events(INSTANCE)) == 5


def test_zrkadlo_lokalny_spool_pod_menom_agenta_hubu(tmp_path: Path):
    """Keď má klon agent.json, lokálne udalosti nesú meno tohto agenta (ako by ich poslal na hub)."""
    reader = _FakeReader([SimpleNamespace(instance=INSTANCE, session="s2", events=_events("s2"))])
    cfg = SimpleNamespace(name="trade-pc", hub_url="http://hub.test:8790", send=True)
    m = _mirror(tmp_path, hub=(cfg, _FakeHubHttp([])), reader=reader)
    m.tick()
    assert m.store.instances()[0]["agent"] == "trade-pc"


def test_zrkadlo_bez_modulu_spool_bezi_dalej(tmp_path: Path, monkeypatch):
    """`tradebot.live.spool` môže pribudnúť neskôr — predvolený reader vtedy nie je a nič nepadá."""
    import builtins

    from tester.webapp.api import live as live_mod

    povodny = builtins.__import__

    def bez_spoolu(name, *a, **k):
        if name == "tradebot.live" and a and a[2] and "spool" in a[2]:
            raise ImportError("no spool")
        if name == "tradebot.live.spool":
            raise ImportError("no spool")
        return povodny(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", bez_spoolu)
    assert live_mod._default_reader(tmp_path / "c.json") is None


def test_vlakno_zrkadla_sa_da_spustit_a_zastavit(tmp_path: Path):
    m = _mirror(tmp_path, hub=None, reader=None, interval=0.05)
    m.start(); m.start()
    assert m.running
    import time as _t
    for _ in range(100):
        if m.ticks:
            break
        _t.sleep(0.01)
    m.stop()
    assert not m.running and m.ticks >= 1


# --------------------------------------------------------------------------- #
# fáza 2b: účty a nasadenia — proxy na hub, admin token, heslo nikde neostáva
# --------------------------------------------------------------------------- #


class _FakeDeployHub:
    """Falošný hub pre `HubHttp`: pamätá si volania (metóda, cesta, token, telo) a odpovedá
    ako hub — `admin` vyžaduje hlavný token, inak 403."""

    def __init__(self, admin_token: str = "hlavny") -> None:
        self.admin_token = admin_token
        self.calls: list[tuple[str, str, str, dict | None]] = []
        self.accounts = [{"id": "ic", "agent": "trade-pc", "platform": "mt5", "label": "IC", "login": "1", "server": "S",
                          "terminal": "", "portable": False, "created": 1.0, "updated": 1.0, "by": "r", "secret_pending": False}]
        self.deployments = [{"id": "d1", "account": "ic", "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p",
                             "config": {"rrRatio": 3.0}, "config_hash": "h", "mode": "enabled", "active": True,
                             "instance": "mt5_1-S_NAS100_3m_ibsnet", "agent": "trade-pc", "applied": None,
                             "live": {"seen": False, "alive": False}}]

    def handler(self, method: str, path: str, token: str, body: dict | None):
        from tester.hub.client import HubError

        self.calls.append((method, path, token, body))
        if method in ("POST", "PATCH", "DELETE") and token != self.admin_token:
            raise HubError(403, "len správca hubu (hlavný token)")
        if path.startswith("/api/agents"):
            return [{"name": "trade-pc", "online": True, "last_seen": "x", "live": {"drivers": ["mt5"], "instances": 0}}]
        if path.startswith("/api/live/accounts"):
            if method == "GET":
                return self.accounts
            if method == "DELETE":
                return {"id": "ic", "deleted": True, "deployments": []}
            return {**self.accounts[0], "secret_pending": bool((body or {}).get("password"))}
        if path.startswith("/api/live/deployments/nie"):
            raise HubError(404, "nasadenie neexistuje")
        if path.startswith("/api/live/deployments"):
            if method == "GET":
                return self.deployments[0] if path.startswith("/api/live/deployments/") else self.deployments
            if method == "DELETE":
                return {"id": "d1", "deleted": False, "active": False}
            return {**self.deployments[0], **{k: v for k, v in (body or {}).items() if k in ("mode", "profile", "config", "active")}}
        if path.startswith("/api/live/audit"):
            return [{"id": 1, "ts": 1.0, "by": "r", "action": "account_create", "account": "ic", "deployment": None, "old": None, "new": {}}]
        if path.startswith("/api/live/export"):
            return []
        raise HubError(404, "Not Found")


@pytest.fixture
def deploy_app(tmp_path: Path, monkeypatch):
    """Webapp s agent.json v tmp (admin token voliteľný) a `HubHttp` presmerovaným na falošný hub."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.hub import client as client_mod, config as hub_config
    from tester.webapp.api import live as live_mod
    from tester.webapp.app import create_app
    from tester.webapp.runner import BacktestRunner
    from tester.webapp.store import RunStore

    live_dir = tmp_path / "live"
    monkeypatch.setattr(live_mod, "LIVE_MIRROR", live_dir / "mirror.sqlite")
    monkeypatch.setattr(live_mod, "LIVE_MIRROR_CURSOR", live_dir / "mirror_cursor.json")
    monkeypatch.setattr(live_mod, "LIVE_CURSOR_WEBAPP", live_dir / "cursor_webapp.json")
    for k in ("TRADEBOT_HUB_URL", "TRADEBOT_HUB_TOKEN", "TRADEBOT_HUB_NAME", "TRADEBOT_HUB_ADMIN_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    cfg_path = tmp_path / "agent.json"
    monkeypatch.setattr(hub_config, "AGENT_CONFIG", cfg_path)
    hub = _FakeDeployHub()

    class FakeHttp(client_mod.HubHttp):
        def _call(self, method, path, data=None, content_type=None, timeout=None):
            import json as _json

            body = _json.loads(data) if data else None
            out = hub.handler(method, path, self.token, body)
            return _json.dumps(out).encode("utf-8"), "application/json"

    monkeypatch.setattr(client_mod, "HubHttp", FakeHttp)

    def make(admin: str = ""):
        hub_config.save(hub_config.AgentConfig(name="notebook", hub_url="http://hub.test:8790", token="agent-token",
                                               admin_token=admin), cfg_path)
        store = RunStore(tmp_path / "runs")
        runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
        return TestClient(create_app(store, runner))

    return make, hub, tmp_path


def test_deploy_proxy_len_na_citanie_bez_admin_tokenu(deploy_app):
    make, hub, tmp = deploy_app
    c = make(admin="")
    assert c.get("/api/live").json()["deploy"] == {"configured": True, "hub_url": "http://hub.test:8790", "admin": False}
    # čítanie ide tokenom agenta
    assert c.get("/api/live/accounts").json()[0]["id"] == "ic"
    assert c.get("/api/live/deployments").json()[0]["id"] == "d1"
    assert c.get("/api/live/agents").json() == [{"name": "trade-pc", "online": True, "last_seen": "x",
                                                 "live": {"drivers": ["mt5"], "instances": 0}}]
    assert c.get("/api/live/audit").json()[0]["action"] == "account_create"
    assert {t for _, _, t, _ in hub.calls} == {"agent-token"}
    # mutácie bez admin tokenu: 403 so slovenskou radou, na hub nič neodíde
    n = len(hub.calls)
    for r in (c.post("/api/live/accounts", json={"agent": "trade-pc", "platform": "mt5", "login": "1"}),
              c.patch("/api/live/accounts/ic", json={"label": "x"}),
              c.delete("/api/live/accounts/ic"),
              c.post("/api/live/deployments", json={"account": "ic", "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p"}),
              c.patch("/api/live/deployments/d1", json={"mode": "paused"}),
              c.delete("/api/live/deployments/d1")):
        assert r.status_code == 403 and "admin_token" in r.json()["detail"]
    assert len(hub.calls) == n


def test_deploy_proxy_mutacie_admin_tokenom_a_heslo_nikde_neostane(deploy_app, monkeypatch):
    make, hub, tmp = deploy_app
    c = make(admin="hlavny")
    assert c.get("/api/live").json()["deploy"]["admin"] is True
    r = c.post("/api/live/accounts", json={"agent": "trade-pc", "platform": "mt5", "label": "IC", "login": "1", "server": "S",
                                          "password": "SuperTajneHeslo42", "user": "Rasto P"})
    assert r.status_code == 200 and r.json()["secret_pending"] is True and "SuperTajne" not in r.text
    m, path, token, body = hub.calls[-1]
    assert (m, token) == ("POST", "hlavny") and path == "/api/live/accounts?by=Rasto%20P"
    assert body["password"] == "SuperTajneHeslo42" and "user" not in body     # na hub ide raz, v tele
    # heslo nie je v žiadnom súbore webapp (zrkadlo, kurzory, agent.json, runs)
    for f in tmp.rglob("*"):
        if f.is_file():
            assert b"SuperTajneHeslo42" not in f.read_bytes(), f
    assert "SuperTajneHeslo42" not in json.dumps(c.get("/api/live/accounts").json())

    assert c.patch("/api/live/accounts/ic", json={"label": "x", "password": "Druhe"}).status_code == 200
    assert hub.calls[-1][0] == "PATCH" and hub.calls[-1][3] == {"label": "x", "password": "Druhe"}
    assert c.delete("/api/live/accounts/ic?force=true&user=r").json()["deleted"] is True
    assert hub.calls[-1][1] == "/api/live/accounts/ic?force=true&by=r"

    # nasadenie: config sa z profilu poskladá vo webapp (repozitár + vlastné) a na hub ide hotový
    r = c.post("/api/live/deployments", json={"account": "ic", "strategy": "ibsninja", "symbol": "MNQ 12-26", "tf": 3,
                                             "profile": "multicharts_mnq_3m", "user": "r"})
    assert r.status_code == 200
    m, path, token, body = hub.calls[-1]
    assert (m, path, token) == ("POST", "/api/live/deployments?by=r", "hlavny")
    assert body["strategy"] == "ibsnet" and body["symbol"] == "MNQ 12-26" and "rrRatio" in body["config"] and body["mode"] == "enabled"
    assert c.post("/api/live/deployments", json={"account": "ic", "strategy": "cudzia", "symbol": "X", "tf": 3, "profile": "p"}).status_code == 422
    assert c.post("/api/live/deployments", json={"account": "ic", "strategy": "ibsnet", "symbol": "X", "tf": 3, "profile": "nie-je"}).status_code == 422
    assert c.post("/api/live/deployments", json={"account": "ic", "strategy": "ibsnet", "symbol": "X", "tf": 3, "profile": ""}).status_code == 422
    # patch: mode ide priamo; profil sa prekladá na config
    assert c.patch("/api/live/deployments/d1", json={"mode": "paused", "user": "r"}).json()["mode"] == "paused"
    assert hub.calls[-1][3] == {"mode": "paused"}
    r = c.patch("/api/live/deployments/d1", json={"profile": "multicharts_mnq_3m"})
    assert r.status_code == 200 and hub.calls[-1][3]["profile"] == "multicharts_mnq_3m" and "rrRatio" in hub.calls[-1][3]["config"]
    assert hub.calls[-2][:2] == ("GET", "/api/live/deployments/d1")     # stratégia nasadenia sa vzala z hubu
    assert c.patch("/api/live/deployments/nie", json={"profile": "multicharts_mnq_3m"}).status_code == 404
    assert c.delete("/api/live/deployments/d1?user=r").json() == {"id": "d1", "deleted": False, "active": False}
    assert hub.calls[-1][1] == "/api/live/deployments/d1?force=false&by=r"
    # profily do výberu
    p = c.get("/api/live/profiles?strategy=ibsnet").json()
    assert "multicharts_mnq_3m" in p["profiles"] and p["strategy"] == "ibsnet"
    assert c.get("/api/live/profiles?strategy=nie").status_code == 422


def test_deploy_proxy_bez_hubu_a_stary_hub(deploy_app, monkeypatch):
    make, hub, tmp = deploy_app
    c = make(admin="hlavny")
    from tester.hub.client import HubError

    povodny = hub.handler

    def stary(method, path, token, body):
        if path.startswith("/api/live/accounts"):
            raise HubError(404, "Not Found")
        if path.startswith("/api/live/deployments"):
            raise OSError("connection refused")
        return povodny(method, path, token, body)

    hub.handler = stary
    r = c.get("/api/live/accounts")
    assert r.status_code == 409 and "staršom kóde" in r.json()["detail"]
    r = c.get("/api/live/deployments")
    assert r.status_code == 502 and "nedostupný" in r.json()["detail"]

    from tester.hub import config as hub_config

    hub_config.AGENT_CONFIG.unlink()
    assert c.get("/api/live").json()["deploy"] == {"configured": False, "hub_url": None, "admin": False}
    assert c.get("/api/live/accounts").status_code == 404
    assert c.post("/api/live/accounts", json={"agent": "a", "platform": "mt5", "login": "1"}).status_code == 404


def test_admin_token_v_configu_a_prostredi(tmp_path: Path, monkeypatch):
    from tester.hub import config as hub_config

    for k in ("TRADEBOT_HUB_URL", "TRADEBOT_HUB_TOKEN", "TRADEBOT_HUB_ADMIN_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    p = tmp_path / "agent.json"
    hub_config.save(hub_config.AgentConfig(name="n", hub_url="http://h", token="t", admin_token="adm"), p)
    cfg = hub_config.load(p)
    assert cfg.admin_token == "adm" and cfg.public()["admin_token"] is True and cfg.public()["token"] is True
    assert json.loads(p.read_text(encoding="utf-8"))["admin_token"] == "adm"
    monkeypatch.setenv("TRADEBOT_HUB_ADMIN_TOKEN", "z-env")
    assert hub_config.load(p).admin_token == "z-env"
    hub_config.save(hub_config.AgentConfig(name="n", hub_url="http://h", token="t"), p)
    monkeypatch.delenv("TRADEBOT_HUB_ADMIN_TOKEN")
    assert hub_config.load(p).admin_token == "" and hub_config.load(p).public()["admin_token"] is False
