"""Karta Live vo webapp (docs/LIVE.md): API nad zrkadlom a zrkadlo samo.

Zrkadlo (`LiveMirror`) sa testuje bez vlákna a bez siete — hub je falošný objekt s `get()`,
lokálny spool falošný reader s `read()`/`commit()`. Stránka číta len zrkadlo, takže API
stačí naplniť `LiveStore` v dočasnom adresári.
"""

from __future__ import annotations

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


def _export_rows(events: list[dict], *, agent: str = "trade-pc", start_id: int = 1) -> list[dict]:
    return [{"id": start_id + i, "agent": agent, "instance": INSTANCE, "session": "a1b2c3d4", "event": ev}
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
