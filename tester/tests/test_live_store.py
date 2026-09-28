"""`tradebot.live.store.LiveStore`: idempotentný príjem, stav inštancie z `hello`/`bar`,
snapshot za posledných N barov (aj zdvojené bary po reštarte), export a kurzor pre zrkadlo."""

from __future__ import annotations

from pathlib import Path

from tradebot.live.schema import instance_id
from tradebot.live.store import LiveStore

INST = instance_id("mt5", "5012345-ICMarkets-Demo", "NAS100", 3, "orbnet")
BT0 = 1_790_000_000_000


def hello(seq: int = 1, session: str = "a1b2c3d4", t: int = BT0) -> dict:
    return {"seq": seq, "t": t, "k": "hello", "schema": 1, "platform": "mt5",
            "account": "5012345-ICMarkets-Demo", "symbol": "NAS100", "tf": 3, "strategy": "orbnet",
            "profile": "nas100_dukas_3m", "session": session, "host": "VM-TRADE-01", "tester": False,
            "config": {"rrRatio": 3.0}, "instrument": {"tick": 0.25}}


def bar(seq: int, i: int, ready: bool = True) -> dict:
    bt = BT0 + i * 180_000
    return {"seq": seq, "t": bt + 180_000, "k": "bar", "bt": bt, "o": 100.0 + i, "h": 101.0 + i,
            "l": 99.0 + i, "c": 100.5 + i, "v": 10, "ready": ready, "mb": 1}


def order(seq: int, i: int) -> dict:
    return {"seq": seq, "t": BT0 + i * 180_000 + 1, "k": "order", "bt": BT0 + i * 180_000, "ready": True,
            "a": "entry", "id": f"L-{i}", "dir": 1, "ot": "limit", "p": {"e": 100.0, "sl": 99.0, "tp": 103.0}}


def fill(seq: int, i: int) -> dict:
    return {"seq": seq, "t": BT0 + i * 180_000 + 5_000, "k": "fill", "ft": BT0 + i * 180_000 + 4_000,
            "id": f"L-{i}", "side": "in", "exit": "", "price": 100.0, "qty": 1, "ready": True}


def test_ingest_is_idempotent_and_touches_instance(tmp_path: Path):
    st = LiveStore(tmp_path / "live.sqlite", clock=lambda: 1_000.0)
    events = [hello(), bar(2, 0, ready=False), bar(3, 1), order(4, 1)]
    assert st.ingest("srv", INST, "a1b2c3d4", events) == 4
    # tá istá dávka znova: nič nové (agent ju po výpadku pošle druhýkrát)
    assert st.ingest("srv", INST, "a1b2c3d4", events) == 0
    # prekrývajúca sa dávka: len nové seq
    assert st.ingest("srv", INST, "a1b2c3d4", [bar(3, 1), bar(5, 2)]) == 1

    inst = st.instance(INST)
    assert inst is not None
    assert inst["platform"] == "mt5" and inst["account"] == "5012345-ICMarkets-Demo"
    assert inst["symbol"] == "NAS100" and inst["tf"] == 3 and inst["strategy"] == "orbnet"
    assert inst["profile"] == "nas100_dukas_3m" and inst["host"] == "VM-TRADE-01"
    assert inst["hello"]["config"] == {"rrRatio": 3.0}
    assert inst["agent"] == "srv" and inst["first_seen"] == 1_000.0 and inst["last_seen"] == 1_000.0
    assert inst["last_bar_ms"] == BT0 + 2 * 180_000
    assert inst["last_t"] == bar(5, 2)["t"] and inst["last_session"] == "a1b2c3d4"
    assert [i["id"] for i in st.instances()] == [INST]
    assert st.instance("nie-je") is None

    # nová session po reštarte: hello zopakuje popis, last_session sa prepne
    assert st.ingest("srv", INST, "ffffffff", [hello(1, "ffffffff", t=BT0 + 10 * 180_000)]) == 1
    assert st.instance(INST)["last_session"] == "ffffffff"


def test_bad_event_is_skipped_not_fatal(tmp_path: Path):
    st = LiveStore(tmp_path / "live.sqlite")
    zle = [hello(), {"seq": 2, "t": BT0, "k": "bar"},            # bar bez OHLC
           {"seq": "3", "t": BT0, "k": "note", "text": "x"},   # seq nie je int
           {"k": "bye"},                                       # chýba seq, t
           {"seq": 4, "t": BT0, "k": "note", "text": "ok", "level": "warn"}]
    assert st.ingest("srv", INST, "a1b2c3d4", zle) == 2
    druhy = [r["event"]["k"] for r in st.events(INST)]
    assert druhy == ["hello", "note"]


def test_events_after_and_kinds(tmp_path: Path):
    st = LiveStore(tmp_path / "live.sqlite")
    st.ingest("srv", INST, "a1b2c3d4", [hello(), bar(2, 0), order(3, 0), bar(4, 1), fill(5, 0)])
    rows = st.events(INST)
    assert [r["seq"] for r in rows] == [1, 2, 3, 4, 5]
    assert rows[0]["id"] == 1 and rows[0]["session"] == "a1b2c3d4" and rows[0]["instance"] == INST
    assert [r["seq"] for r in st.events(INST, after=rows[2]["id"])] == [4, 5]
    assert [r["seq"] for r in st.events(INST, kinds=["bar", "fill"])] == [2, 4, 5]
    assert [r["seq"] for r in st.events(INST, limit=2)] == [1, 2]
    assert st.events("ina-instancia") == []


def test_snapshot_window_and_duplicate_bars(tmp_path: Path):
    st = LiveStore(tmp_path / "live.sqlite")
    events = [hello()] + [bar(2 + i, i) for i in range(10)]
    events += [order(20, 3), order(21, 8), fill(22, 8),
               {"seq": 23, "t": BT0, "k": "event", "bt": BT0 + 8 * 180_000, "ts": 1, "z": "z8", "f": "armed", "to": "filled"},
               {"seq": 24, "t": BT0, "k": "draw", "bt": BT0 + 9 * 180_000, "d": [{"t": "box", "id": "z8"}]},
               {"seq": 25, "t": BT0, "k": "note", "text": "neskorý bar", "level": "warn"},
               {"seq": 26, "t": BT0, "k": "stat", "stats": {"trades": 2, "adapter_fills": 1}}]
    st.ingest("srv", INST, "a1b2c3d4", events)
    # reštart: nová session prehrá posledné bary znova (ready:false) — snapshot ich nezdvojí
    st.ingest("srv", INST, "ffffffff", [hello(1, "ffffffff"), bar(2, 8, ready=False), bar(3, 9, ready=False), bar(4, 10)])

    s = st.snapshot(INST, bars=5)
    assert s["instance"]["id"] == INST
    assert [b["bt"] for b in s["bars"]] == [BT0 + i * 180_000 for i in range(6, 11)]
    assert len({b["bt"] for b in s["bars"]}) == 5
    # z posledných barov platí posledný zápis (nová session)
    assert s["bars"][-2]["ready"] is False and s["bars"][-1]["ready"] is True
    # ordery/udalosti/kresby/fills len z okna (order na bare 3 vypadne)
    assert [o["id"] for o in s["orders"]] == ["L-8"]
    assert [e["z"] for e in s["events"]] == ["z8"]
    assert s["draw"][0]["d"][0]["id"] == "z8"
    assert [f["id"] for f in s["fills"]] == ["L-8"]
    assert s["stats"] == {"trades": 2, "adapter_fills": 1}
    assert [n["text"] for n in s["notes"]] == ["neskorý bar"]

    # celé okno
    assert len(st.snapshot(INST, bars=500)["bars"]) == 11
    assert len(st.snapshot(INST, bars=500)["orders"]) == 2
    prazdny = st.snapshot("nie-je")
    assert prazdny["instance"] is None and prazdny["bars"] == [] and prazdny["stats"] is None


def test_sessions_summary_live_flag_and_snapshot_per_session(tmp_path: Path):
    """Dva behy jednej inštancie: starší ukončený (`bye`), novší živý — prehľad behov,
    príznak `live` podľa hodín a snapshot/events obmedzené na jeden beh."""
    hodiny = {"now": (BT0 + 20 * 180_000) / 1000.0}
    st = LiveStore(tmp_path / "live.sqlite", clock=lambda: hodiny["now"])
    # beh 1: hello, 5 barov, order + fill, stat, bye
    stary = [hello()] + [bar(2 + i, i) for i in range(5)] + [order(7, 2), fill(8, 2),
             {"seq": 9, "t": BT0, "k": "stat", "stats": {"trades": 1}},
             {"seq": 10, "t": BT0 + 5 * 180_000 + 1_000, "k": "bye", "reason": "terminated"}]
    st.ingest("srv", INST, "a1b2c3d4", stary)
    # beh 2 (reštart, iný agent, iný profil): prehrá bary 3–4 (ready:false), potom 5–9 naživo, bez bye
    h2 = hello(1, "ffffffff", t=BT0 + 6 * 180_000)
    h2["profile"] = "nas100_v2"
    novy = [h2, bar(2, 3, ready=False), bar(3, 4, ready=False)] + [bar(4 + i, 5 + i) for i in range(5)]
    novy += [order(20, 7), order(21, 8), fill(22, 8), fill(23, 9)]
    st.ingest("srv2", INST, "ffffffff", novy)

    behy = st.sessions(INST)
    assert [s["session"] for s in behy] == ["ffffffff", "a1b2c3d4"]        # najnovší prvý
    s1, s2 = behy[1], behy[0]
    assert s1["started"] == BT0 and s1["ended"] == BT0 + 5 * 180_000 + 1_000 and s1["reason"] == "terminated"
    assert s1["bars"] == 5 and s1["fills"] == 1 and s1["orders"] == 1 and s1["agent"] == "srv"
    assert s1["first_bar_ms"] == BT0 and s1["last_bar_ms"] == BT0 + 4 * 180_000
    assert s1["profile"] == "nas100_dukas_3m" and s1["live"] is False
    assert s2["started"] == BT0 + 6 * 180_000 and s2["ended"] is None and s2["reason"] is None
    assert s2["bars"] == 7 and s2["fills"] == 2 and s2["orders"] == 2 and s2["agent"] == "srv2"
    assert s2["first_bar_ms"] == BT0 + 3 * 180_000 and s2["last_bar_ms"] == BT0 + 9 * 180_000
    assert s2["last_t"] == bar(0, 9)["t"] and s2["profile"] == "nas100_v2"
    # posledná udalosť behu 2 je bar 9 (t = BT0 + 10 barov); teraz je BT0 + 20 barov → 10 barov ticha > 3
    assert s2["live"] is False
    hodiny["now"] = (BT0 + 12 * 180_000) / 1000.0                          # 2 bary od poslednej udalosti
    assert st.sessions(INST)[0]["live"] is True
    assert st.sessions("nie-je") == []

    # snapshot behu 1: len jeho bary/ordery/fills/stat/bye, aj keď beh 2 tie isté bary prepísal
    a = st.snapshot(INST, session="a1b2c3d4")
    assert a["session"] == "a1b2c3d4"
    assert [b["bt"] for b in a["bars"]] == [BT0 + i * 180_000 for i in range(5)]
    assert all(b["ready"] for b in a["bars"])
    assert [o["id"] for o in a["orders"]] == ["L-2"] and [f["id"] for f in a["fills"]] == ["L-2"]
    assert a["stats"] == {"trades": 1} and [n["k"] for n in a["notes"]] == ["bye"]
    # snapshot behu 2: celý beh (7 barov, replay ready:false), bez stat behu 1
    b = st.snapshot(INST, session="ffffffff")
    assert [x["bt"] for x in b["bars"]] == [BT0 + i * 180_000 for i in range(3, 10)]
    assert b["bars"][0]["ready"] is False and b["stats"] is None and b["notes"] == []
    assert [o["id"] for o in b["orders"]] == ["L-7", "L-8"] and [f["id"] for f in b["fills"]] == ["L-8", "L-9"]
    assert len(st.snapshot(INST, session="ffffffff", bars=2)["bars"]) == 2
    # bez session: ako doteraz — naprieč behmi, posledný zápis baru platí
    c = st.snapshot(INST)
    assert c["session"] is None and [x["bt"] for x in c["bars"]] == [BT0 + i * 180_000 for i in range(10)]
    assert c["bars"][3]["ready"] is False and c["stats"] == {"trades": 1}
    assert st.snapshot("nie-je", session="x")["session"] == "x"

    # events so session
    assert [r["seq"] for r in st.events(INST, session="a1b2c3d4", kinds=["bar"])] == [2, 3, 4, 5, 6]
    assert [r["session"] for r in st.events(INST, session="ffffffff", limit=1)] == ["ffffffff"]
    assert len(st.events(INST, limit=100)) == len(stary) + len(novy)


def test_export_and_cursor_for_mirror(tmp_path: Path):
    hub = LiveStore(tmp_path / "hub.sqlite")
    zrkadlo = LiveStore(tmp_path / "mirror.sqlite")
    assert hub.cursor() == 0 and hub.export() == []
    hub.ingest("srv", INST, "a1b2c3d4", [hello(), bar(2, 0), bar(3, 1)])
    ina = instance_id("ninjatrader", "Sim101", "MNQ 12-26", 3, "ibsnet")
    hub.ingest("nt-pc", ina, "deadbeef", [bar(1, 0)])
    assert hub.cursor() == 4

    # zrkadlo ťahá po kúskoch a nesie meno agenta ďalej
    kurzor = 0
    while True:
        rows = hub.export(after=kurzor, limit=2)
        if not rows:
            break
        for r in rows:
            assert r["agent"] in ("srv", "nt-pc")
            zrkadlo.ingest(r["agent"], r["instance"], r["session"], [r["event"]])
        kurzor = rows[-1]["id"]
    assert kurzor == 4
    assert {i["id"]: i["agent"] for i in zrkadlo.instances()} == {INST: "srv", ina: "nt-pc"}
    assert zrkadlo.cursor() == 4
    # opakovaný export od nuly nič nezdvojí
    for r in hub.export():
        assert zrkadlo.ingest(r["agent"], r["instance"], r["session"], [r["event"]]) == 0
    assert hub.export(after=4) == []
