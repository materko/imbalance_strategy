"""`tradebot.live.spool.SpoolReader` a `tradebot.live.shipper.LiveShipper`: kurzor prežije
nový reader, neúplný riadok sa nečíta, rotácia súboru drží session, rozbitý riadok sa preskočí,
`max_events` delí dávku uprostred súboru; shipper proti falošnému HTTP — výpadok = kurzor stojí,
po návrate sa nič nepošle dvakrát (počíta falošný hub cez `LiveStore.ingest`)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tradebot.live.schema import instance_id
from tradebot.live.shipper import LiveShipper
from tradebot.live.spool import Batch, SpoolReader, default_roots
from tradebot.live.store import LiveStore

INST = instance_id("ninjatrader", "Sim101", "MNQ 12-26", 3, "ibsnet")
INST2 = instance_id("mt5", "5012345-ICMarkets-Demo", "NAS100", 3, "orbnet")
BT0 = 1_790_000_000_000


def hello(seq: int, session: str, platform: str = "ninjatrader") -> dict:
    return {"seq": seq, "t": BT0, "k": "hello", "schema": 1, "platform": platform, "account": "Sim101",
            "symbol": "MNQ 12-26", "tf": 3, "strategy": "ibsnet", "profile": "p", "session": session,
            "host": "PC", "tester": False, "config": {}, "instrument": {}}


def bar(seq: int, i: int) -> dict:
    bt = BT0 + i * 180_000
    return {"seq": seq, "t": bt + 180_000, "k": "bar", "bt": bt, "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5,
            "v": 3, "ready": True, "mb": 0}


def line(ev: dict) -> bytes:
    return json.dumps(ev, separators=(",", ":")).encode("utf-8") + b"\n"


def spool_file(root: Path, instance: str, session: str, stamp: str = "20260928-100000") -> Path:
    d = root / instance
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{stamp}_{session}.jsonl"


@pytest.fixture
def reader(tmp_path: Path):
    root = tmp_path / "spool"
    root.mkdir()
    return SpoolReader([root], tmp_path / "cursor.json"), root


def test_read_commit_and_cursor_survives_new_reader(reader, tmp_path: Path):
    r, root = reader
    f = spool_file(root, INST, "a1b2c3d4")
    f.write_bytes(line(hello(1, "a1b2c3d4")) + line(bar(2, 0)) + line(bar(3, 1)))
    assert r.status()["pending_bytes"] == f.stat().st_size

    batches = r.read()
    assert len(batches) == 1
    b = batches[0]
    assert isinstance(b, Batch)
    assert b.instance == INST and b.session == "a1b2c3d4" and b.path == f
    assert [e["seq"] for e in b.events] == [1, 2, 3]
    assert b.start_offset == 0 and b.end_offset == f.stat().st_size
    # bez commitu to isté znova
    assert [e["seq"] for e in r.read()[0].events] == [1, 2, 3]
    r.commit(b)
    assert r.read() == [] and r.status()["pending_bytes"] == 0
    assert json.loads((tmp_path / "cursor.json").read_text())[str(f)] == b.end_offset

    # nový reader (reštart agenta) číta od uloženého kurzora; session vezme z hello v súbore
    with open(f, "ab") as fh:
        fh.write(line(bar(4, 2)))
    r2 = SpoolReader([root], tmp_path / "cursor.json")
    b2 = r2.read()[0]
    assert [e["seq"] for e in b2.events] == [4] and b2.session == "a1b2c3d4"
    assert b2.start_offset == b.end_offset


def test_partial_last_line_waits_for_newline(reader):
    r, root = reader
    f = spool_file(root, INST, "a1b2c3d4")
    cely = line(hello(1, "a1b2c3d4"))
    kus = line(bar(2, 0))
    f.write_bytes(cely + kus[:-10])            # zapisovač je uprostred riadku
    b = r.read()[0]
    assert [e["seq"] for e in b.events] == [1] and b.end_offset == len(cely)
    r.commit(b)
    assert r.read() == []
    with open(f, "ab") as fh:                  # dopíše zvyšok aj `\n`
        fh.write(kus[-10:])
    b = r.read()[0]
    assert [e["seq"] for e in b.events] == [2] and b.start_offset == len(cely) and b.end_offset == len(cely) + len(kus)
    # súbor len s neúplným riadkom nedá žiadnu dávku
    g = spool_file(root, INST2, "eeeeeeee")
    g.write_bytes(b'{"seq":1,"t":1,"k":"bye"')
    r.commit(b)
    assert r.read() == []


def test_two_instances_and_rotation_keep_session(reader):
    r, root = reader
    a = spool_file(root, INST, "a1b2c3d4")
    a.write_bytes(line(hello(1, "a1b2c3d4")) + line(bar(2, 0)))
    m = spool_file(root, INST2, "ffffffff")
    m.write_bytes(line(hello(1, "ffffffff", "mt5")) + line(bar(2, 0)))
    # rotácia dňa: druhý súbor tej istej session, hello sa zopakuje, seq pokračuje
    a2 = spool_file(root, INST, "a1b2c3d4", stamp="20260929-000000")
    a2.write_bytes(line({**hello(3, "a1b2c3d4")}) + line(bar(4, 1)))
    # súbor bez hello (hello ešte nedopísaný): session z názvu
    a3 = spool_file(root, INST, "0badc0de", stamp="20260930-000000")
    a3.write_bytes(line(bar(1, 5)))

    batches = r.read()
    # poradie (instance, názov súboru): „mt5_…" je pred „ninjatrader_…", súbory podľa času štartu
    assert [(b.instance, b.path.name, b.session) for b in batches] == [
        (INST2, m.name, "ffffffff"),
        (INST, a.name, "a1b2c3d4"), (INST, a2.name, "a1b2c3d4"), (INST, a3.name, "0badc0de")]
    assert [[e["seq"] for e in b.events] for b in batches] == [[1, 2], [1, 2], [3, 4], [1]]
    st = r.status()
    assert len(st["files"]) == 4 and st["roots"] == [str(root)]


def test_bad_line_is_skipped_but_consumed(reader, caplog):
    r, root = reader
    f = spool_file(root, INST, "a1b2c3d4")
    f.write_bytes(line(hello(1, "a1b2c3d4")) + b"toto nie je json\n" + b'{"seq":9,"t":1,"k":"neznamy"}\n'
                  + b"\n" + line(bar(2, 0)))
    with caplog.at_level("WARNING", logger="tradebot.live.spool"):
        b = r.read()[0]
    assert [e["seq"] for e in b.events] == [1, 2]
    assert b.end_offset == f.stat().st_size
    assert sum("preskakujem" in m for m in caplog.messages) == 2


def test_max_events_splits_batch_mid_file(reader):
    r, root = reader
    f = spool_file(root, INST, "a1b2c3d4")
    riadky = [line(hello(1, "a1b2c3d4"))] + [line(bar(2 + i, i)) for i in range(9)]
    f.write_bytes(b"".join(riadky))
    druha = instance_id("ninjatrader", "Sim102", "MNQ 12-26", 3, "ibsnet")   # radí sa až za INST
    g = spool_file(root, druha, "ffffffff")
    g.write_bytes(line(hello(1, "ffffffff")))

    b = r.read(max_events=4)
    assert len(b) == 1 and [e["seq"] for e in b[0].events] == [1, 2, 3, 4]
    assert b[0].end_offset == sum(len(x) for x in riadky[:4])
    r.commit(b[0])
    b = r.read(max_events=4)
    assert [e["seq"] for e in b[0].events] == [5, 6, 7, 8] and b[0].session == "a1b2c3d4"
    assert b[0].start_offset == sum(len(x) for x in riadky[:4])
    r.commit(b[0])
    # zvyšok prvého súboru (2 udalosti) + druhý súbor (1) sa zmestí do jednej dávky po 4
    b = r.read(max_events=4)
    assert [[e["seq"] for e in x.events] for x in b] == [[9, 10], [1]]
    assert b[0].end_offset == f.stat().st_size and b[1].instance == druha
    for x in b:
        r.commit(x)
    assert r.read() == []


def test_reads_while_writer_holds_file_open(reader):
    """Zapisovač drží súbor otvorený na append (ako `StreamWriter` s `FileShare.ReadWrite`);
    reader ho číta bez zamknutia a vidí len to, čo je flushnuté."""
    r, root = reader
    f = spool_file(root, INST, "a1b2c3d4")
    with open(f, "ab") as pisar:
        pisar.write(line(hello(1, "a1b2c3d4")))
        pisar.flush()
        b = r.read()[0]
        assert [e["seq"] for e in b.events] == [1]
        r.commit(b)
        pisar.write(line(bar(2, 0))[:-1])       # bez `\n`
        pisar.flush()
        assert r.read() == []
        pisar.write(b"\n")
        pisar.flush()
        assert [e["seq"] for e in r.read()[0].events] == [2]


def test_default_roots_env_and_dedupe(tmp_path: Path, monkeypatch):
    a = tmp_path / "a"
    a.mkdir()
    monkeypatch.setenv("TRADEBOT_NT_DIR", str(tmp_path / "nie-je-nt"))
    monkeypatch.setenv("TRADEBOT_MT5_COMMON", str(tmp_path / "nie-je-mt5"))
    monkeypatch.setenv("TRADEBOT_LIVE_SPOOL", os.pathsep.join([str(a), str(tmp_path / "chyba"), str(a), ""]))
    assert default_roots() == [a]
    monkeypatch.delenv("TRADEBOT_LIVE_SPOOL")
    assert default_roots() == []
    # „nainštalovaný" NinjaTrader a MT5 (podľa značiek adresárov)
    nt = tmp_path / "nt"
    (nt / "bin" / "Custom").mkdir(parents=True)
    (nt / "TradeBot" / "spool").mkdir(parents=True)
    mt = tmp_path / "mt5common"
    (mt / "TradeBot" / "spool").mkdir(parents=True)
    monkeypatch.setenv("TRADEBOT_NT_DIR", str(nt))
    monkeypatch.setenv("TRADEBOT_MT5_COMMON", str(mt))
    assert default_roots() == [nt / "TradeBot" / "spool", mt / "TradeBot" / "spool"]


# --------------------------------------------------------------------------- #
# shipper
# --------------------------------------------------------------------------- #


class FakeTransport:
    """Falošný `Transport` (tradebot.live.transport): `push_events` ukladá do `LiveStore` ako
    skutočný hub, `pull_export` z neho číta; `down` = výpadok (výnimka)."""

    def __init__(self, store: LiveStore) -> None:
        self.store = store
        self.down = False
        self.pushes: list[tuple[str, list[dict]]] = []

    def push_events(self, agent: str, batches: list[dict]) -> dict:
        if self.down:
            raise OSError("hub je mimo")
        self.pushes.append((agent, batches))
        n = 0
        for b in batches:
            n += self.store.ingest(agent, b["instance"], b["session"], b["events"])
        return {"accepted": n}

    def pull_export(self, after: int = 0, limit: int = 5000) -> list[dict]:
        if self.down:
            raise OSError("hub je mimo")
        return self.store.export(after=after, limit=limit)


class FakeHub:
    """Falošné **HTTP** (starý tvar `http` shipperu): `post` ukladá do `LiveStore` ako skutočný
    hub; `down` = výpadok. Shipper ho zabalí do `HttpTransport` — starí volajúci fungujú ďalej."""

    def __init__(self, store: LiveStore) -> None:
        self.store = store
        self.down = False
        self.posts: list[dict] = []

    def post(self, path: str, body: dict | None = None) -> dict:
        assert path == "/api/live/events"
        if self.down:
            raise OSError("hub je mimo")
        self.posts.append(body)
        n = 0
        for b in body["batches"]:
            n += self.store.ingest(body["agent"], b["instance"], b["session"], b["events"])
        return {"accepted": n}


def test_shipper_outage_keeps_cursor_and_nothing_is_sent_twice(reader, tmp_path: Path):
    r, root = reader
    hub_store = LiveStore(tmp_path / "hub.sqlite")
    hub = FakeHub(hub_store)
    s = LiveShipper(r, hub, "nt-pc", batch_events=3, max_batches=10)

    f = spool_file(root, INST, "a1b2c3d4")
    f.write_bytes(line(hello(1, "a1b2c3d4")) + b"".join(line(bar(2 + i, i)) for i in range(6)))
    hub.down = True
    out = s.pump()
    assert out["sent"] == 0 and out["error"] and "hub je mimo" in out["error"]
    assert s.status()["last_error"] and s.status()["last_ok"] is None
    assert not (tmp_path / "cursor.json").exists() and r.status()["pending_bytes"] == f.stat().st_size

    hub.down = False
    out = s.pump()
    assert out["sent"] == 7 and out["accepted"] == 7 and out["rounds"] == 3 and out["error"] is None
    assert [len(p["batches"][0]["events"]) for p in hub.posts] == [3, 3, 1]
    assert hub.posts[0]["agent"] == "nt-pc" and hub.posts[0]["batches"][0]["session"] == "a1b2c3d4"
    assert r.status()["pending_bytes"] == 0
    st = s.status()
    assert st["last_error"] is None and st["last_ok"] and st["sent_total"] == 7 and st["accepted_total"] == 7
    assert st["reader"]["pending_bytes"] == 0
    assert hub_store.instance(INST)["last_bar_ms"] == BT0 + 5 * 180_000

    # nič nové = nič neposlané; ďalšie riadky idú raz
    assert s.pump() == {"sent": 0, "accepted": 0, "rounds": 0, "error": None}
    with open(f, "ab") as fh:
        fh.write(line(bar(8, 6)))
    assert s.pump()["accepted"] == 1
    assert [x["seq"] for x in (e["event"] for e in hub_store.events(INST))] == list(range(1, 9))


def test_shipper_failure_mid_way_resends_only_unconfirmed(reader, tmp_path: Path):
    """Padne druhý POST: prvá dávka je potvrdená (kurzor posunutý), druhá sa pošle po návrate —
    a keby hub prvú dostal, ale odpoveď sa stratila, `accepted` bude 0 a nič sa nezdvojí."""
    r, root = reader
    hub_store = LiveStore(tmp_path / "hub.sqlite")

    class Flaky(FakeHub):
        def post(self, path, body=None):
            out = super().post(path, body)
            if len(self.posts) == 2:
                raise OSError("spojenie padlo po prijatí")   # hub dávku má, agent o tom nevie
            return out

    hub = Flaky(hub_store)
    s = LiveShipper(r, hub, "nt-pc", batch_events=2)
    f = spool_file(root, INST, "a1b2c3d4")
    f.write_bytes(line(hello(1, "a1b2c3d4")) + b"".join(line(bar(2 + i, i)) for i in range(4)))
    out = s.pump()
    assert out["sent"] == 2 and out["error"]
    assert hub_store.cursor() == 4                         # hub má aj „stratenú" dávku
    out = s.pump()
    assert out["sent"] == 3 and out["accepted"] == 1 and out["error"] is None   # 2 zopakované + 1 nová
    assert [e["seq"] for e in hub_store.events(INST)] == [1, 2, 3, 4, 5]   # nič zdvojené
    assert s.status()["sent_total"] == 5 and s.status()["accepted_total"] == 3


def test_shipper_over_transport_outage_and_resume(reader, tmp_path: Path):
    """To isté cez `Transport` (nie HTTP): výpadok = kurzor stojí, po návrate raz; shipper HTTP
    cesty nepozná — vidí len `push_events(agent, batches)`."""
    from tradebot.live.transport import HttpTransport, Transport, as_transport

    r, root = reader
    hub_store = LiveStore(tmp_path / "hub.sqlite")
    t = FakeTransport(hub_store)
    assert isinstance(t, Transport) and as_transport(t) is t
    s = LiveShipper(r, t, "nt-pc", batch_events=4)
    assert s.transport is t and s.http is t          # bez podkladového HTTP je `http` transport sám

    f = spool_file(root, INST, "a1b2c3d4")
    f.write_bytes(line(hello(1, "a1b2c3d4")) + b"".join(line(bar(2 + i, i)) for i in range(5)))
    t.down = True
    assert s.pump()["sent"] == 0 and r.status()["pending_bytes"] > 0
    t.down = False
    out = s.pump()
    assert out == {"sent": 6, "accepted": 6, "rounds": 2, "error": None}
    assert [(a, [b["instance"] for b in bs]) for a, bs in t.pushes] == [("nt-pc", [INST])] * 2
    assert t.pushes[0][1][0]["session"] == "a1b2c3d4" and len(t.pushes[0][1][0]["events"]) == 4
    assert r.status()["pending_bytes"] == 0 and hub_store.cursor() == 6
    assert [x["event"]["seq"] for x in t.pull_export(after=4)] == [5, 6]

    # starý HTTP klient sa zabalí; `as_transport` odmietne nezmysel
    hub = FakeHub(hub_store)
    s2 = LiveShipper(r, hub, "nt-pc")
    assert isinstance(s2.transport, HttpTransport) and s2.http is hub
    with pytest.raises(TypeError):
        as_transport(object())


def test_shipper_max_batches_bounds_one_pump(reader, tmp_path: Path):
    r, root = reader
    hub = FakeHub(LiveStore(tmp_path / "hub.sqlite"))
    s = LiveShipper(r, hub, "nt-pc", batch_events=1, max_batches=2)
    f = spool_file(root, INST, "a1b2c3d4")
    f.write_bytes(line(hello(1, "a1b2c3d4")) + line(bar(2, 0)) + line(bar(3, 1)))
    assert s.pump()["sent"] == 2
    assert s.pump()["sent"] == 1
    assert s.pump()["sent"] == 0
