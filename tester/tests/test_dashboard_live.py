"""`tester.dashboard.live`: obchody z fillov (aj po častiach), smer a SL z zámeru enginu, zisk s hodnotou
bodu z `hello`, osud signálov, stav inštancie a id nastavenia stránky z mena profilu."""

from __future__ import annotations

from pathlib import Path

from tester.dashboard.live import base_strategy, build_live, setting_id
from tradebot.live.schema import instance_id
from tradebot.live.store import LiveStore

INST = instance_id("ninjatrader", "DEMO1", "MNQ", 3, "vwaporbnet")
T0 = 1_792_000_000_000
MIN = 60_000


def hello(seq: int, t: int, session: str = "s1") -> dict:
    return {"seq": seq, "t": t, "k": "hello", "schema": 1, "platform": "ninjatrader", "account": "DEMO1",
            "symbol": "MNQ", "tf": 3, "strategy": "vwaporbnet", "profile": "PRESIEL_SMERNICAMI_VWAP_ORB_CS_1",
            "session": session, "host": "PC", "tester": False, "config": {},
            "instrument": {"symbol": "MNQ", "tick_size": 0.25, "point_value": 2.0}}


def entry(seq: int, t: int, oid: str, d: int, e: float, sl: float, tp: float, ready: bool = True) -> dict:
    return {"seq": seq, "t": t, "k": "order", "bt": t - 3 * MIN, "ready": ready, "a": "entry", "id": oid, "dir": d,
            "ot": "Market", "r": "prerazenie New York", "p": {"dir": d, "e": e, "sl": sl, "tp": tp, "q": 2.0, "sd": abs(e - sl)}}


def fill(seq: int, t: int, oid: str, side: str, price: float, qty: float, exit_name: str = "") -> dict:
    return {"seq": seq, "t": t, "k": "fill", "ft": t, "id": oid, "side": side, "exit": exit_name, "price": price,
            "qty": qty, "ready": True}


def cancel(seq: int, t: int, oid: str, reason: str) -> dict:
    return {"seq": seq, "t": t, "k": "order", "bt": t - 3 * MIN, "ready": True, "a": "cancel", "id": oid, "r": reason}


def test_trades_signals_and_status(tmp_path: Path) -> None:
    path = tmp_path / "mirror.sqlite"
    st = LiveStore(path)
    st.ingest("nas", INST, "s1", [
        hello(1, T0),
        entry(2, T0 + 1 * MIN, "orb:1", 1, 100.0, 90.0, 105.0, ready=False),   # prehrávanie histórie — nepočíta sa
        entry(3, T0 + 10 * MIN, "orb:2", 1, 100.0, 90.0, 105.0),
        fill(4, T0 + 11 * MIN, "orb:2", "in", 100.25, 2.0),
        fill(5, T0 + 20 * MIN, "orb:2", "out", 105.0, 1.0, "Profit target"),
        fill(6, T0 + 20 * MIN + 50, "orb:2", "out", 105.0, 1.0, "Profit target"),
        entry(7, T0 + 30 * MIN, "orb:3", -1, 200.0, 210.0, 195.0),
        fill(8, T0 + 31 * MIN, "orb:3", "in", 200.0, 1.0),
        fill(9, T0 + 40 * MIN, "orb:3", "out", 210.0, 1.0, "Stop loss"),
        entry(10, T0 + 50 * MIN, "orb:4", 1, 300.0, 290.0, 305.0),
        cancel(11, T0 + 53 * MIN, "orb:4", "nevyplnené"),
        entry(12, T0 + 60 * MIN, "orb:5", 1, 400.0, 390.0, 405.0),
        fill(13, T0 + 61 * MIN, "orb:5", "in", 400.0, 1.0),
        fill(14, T0 + 62 * MIN, "zz:9", "out", 1.0, 1.0, "Stop loss"),         # výstup bez vstupu
    ])
    st.close()
    live = build_live(path, now_ms=T0 + 70 * MIN)
    (inst,) = live["instances"]
    assert inst["strategy"] == "vwaporb" and inst["setting"] == "vwaporb-1"
    assert inst["profile"] == "PRESIEL_SMERNICAMI_VWAP_ORB_CS_1"
    assert inst["status"] == "beží" and not inst["stale"]
    t1, t2 = inst["trades"]
    assert (t1["dir"], t1["entry"], t1["exit"], t1["qty"], t1["reason"]) == ("long", 100.25, 105.0, 2.0, "take_profit")
    assert t1["pnl"] == round((105.0 - 100.25) * 2 * 2.0, 2) and t1["sl"] == 90.0
    assert t1["r"] == round(4.75 / 10.0, 3)
    assert (t2["dir"], t2["pnl"], t2["reason"], t2["r"]) == ("short", -20.0, "stop_loss", -1.0)
    assert [o["id"] for o in inst["open"]] == ["orb:5"]
    assert inst["orphan_fills"] == 1
    res = {s["id"]: s["result"] for s in inst["signals"]}
    assert res == {"orb:2": "vyplnený", "orb:3": "vyplnený", "orb:4": "zrušený: nevyplnené", "orb:5": "vyplnený"}


def test_bye_stops_and_old_silence_is_stale(tmp_path: Path) -> None:
    path = tmp_path / "mirror.sqlite"
    st = LiveStore(path)
    st.ingest("nas", INST, "s1", [hello(1, T0), {"seq": 2, "t": T0 + MIN, "k": "bye", "reason": "deinit"}])
    st.close()
    (inst,) = build_live(path, now_ms=T0 + 2 * MIN)["instances"]
    assert inst["status"] == "zastavená"
    (inst,) = build_live(path, now_ms=T0 + 10 * 86_400_000)["instances"]
    assert inst["stale"]


def test_missing_mirror_and_names(tmp_path: Path) -> None:
    live = build_live(tmp_path / "nie.sqlite")
    assert live["instances"] == [] and "error" in live
    assert base_strategy("ibsentrynet") == "ibsentry" and base_strategy("vwapadxnet") == "vwapadx"
    assert base_strategy("ibsentryneteod") == "ibsentry" and base_strategy("noaneteod") == "noa"
    assert setting_id("vwaporbneteod", "SMERNICE_CS_EOD_VWAP_ORB_3") == "vwaporb-3"
    assert setting_id("vwapadxnet", "SMERNICE_CS_VWAP_ADX_Pullback_2") == "vwapadx-2"
    assert setting_id("ibsentrynet", r"TradeBot\profiles\x\PRESIEL_SMERNICAMI_IBS_Entry_Zone_CS_1.json") == "ibsentry-1"
    assert setting_id("ibsnet", "multicharts_mnq_3m") is None


def bar(seq: int, t: int, o: float, h: float, l: float, c: float) -> dict:
    return {"seq": seq, "t": t, "k": "bar", "bt": t - 3 * MIN, "o": o, "h": h, "l": l, "c": c, "v": 10.0, "ready": True, "mb": 0}


def test_obchod_bez_zatvorenia_v_telemetrii_nie_je_otvoreny(tmp_path: Path) -> None:
    """16. 10. 2026 NT VWAP ORB: reštart platformy, zatvorenie neprišlo — neskorší vstup alebo prechod SL / TP ho vyradí."""
    path = tmp_path / "mirror.sqlite"
    st = LiveStore(path)
    st.ingest("nas", INST, "s1", [hello(1, T0), entry(2, T0 + 10 * MIN, "orb:1", -1, 200.0, 210.0, 190.0),
                                  fill(3, T0 + 11 * MIN, "orb:1", "in", 200.0, 1.0)])
    st.ingest("nas", INST, "s2", [hello(1, T0 + 60 * MIN, "s2"), entry(2, T0 + 70 * MIN, "orb:2", -1, 195.0, 205.0, 185.0),
                                  fill(3, T0 + 71 * MIN, "orb:2", "in", 195.0, 1.0)])
    st.close()
    (inst,) = build_live(path, now_ms=T0 + 80 * MIN)["instances"]
    assert [o["id"] for o in inst["open"]] == ["orb:2"]
    assert any("orb:1" in n["text"] and n["level"] == "warn" for n in inst["notes"])
    assert inst["trades"] == []

    path2 = tmp_path / "m2.sqlite"
    st = LiveStore(path2)
    st.ingest("nas", INST, "s1", [hello(1, T0), entry(2, T0 + 10 * MIN, "orb:1", -1, 200.0, 210.0, 190.0),
                                  fill(3, T0 + 11 * MIN, "orb:1", "in", 200.0, 1.0),
                                  bar(4, T0 + 15 * MIN, 199.0, 200.0, 195.0, 196.0)])
    st.close()
    (inst,) = build_live(path2, now_ms=T0 + 20 * MIN)["instances"]
    assert [o["id"] for o in inst["open"]] == ["orb:1"]            # SL ani TP nepadli — stále otvorený
    st = LiveStore(path2)
    st.ingest("nas", INST, "s1", [bar(5, T0 + 30 * MIN, 196.0, 197.0, 189.0, 190.0)])   # TP 190 prejdený
    st.close()
    (inst,) = build_live(path2, now_ms=T0 + 35 * MIN)["instances"]
    assert inst["open"] == []
