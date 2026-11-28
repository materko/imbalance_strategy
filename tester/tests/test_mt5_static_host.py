"""Statická fasáda C# jadra pre MetaTrader 5 (`StaticHost`, globálny namespace).

MQL5 vie z .NET assembly volať len verejné statické metódy tried **bez namespace** a len
s jednoduchými typmi, preto má jadro fasádu s handle. Test ju volá tak, ako ju bude volať Expert
Advisor (`tradebot/adapters/mt5/TradeBotEA.mqh`): uzavreté HTF bary po jednom cez `FeedHtf`, bar
grafu cez `OnBar` — a výsledok musí byť **presne** to, čo dá ten istý engine cez most do Freqtrade
s oknom HTF z Python strany.

pythonnet triedu v globálnom namespace neponúka ako modul, preto ide volanie cez reflexiu —
presne tak „naslepo" ako z MQL5.
"""

from __future__ import annotations

import json

import pytest

from tradebot.core import load_profile
from tradebot.core.candles import resample_ohlcv
from tradebot.core.types import Bar
from tradebot.strategies import get_spec
from tradebot.core.paths import TEST_PROFILES_DIR  # noqa: E402


class _Reflected:
    """`host.Metoda(...)` -> `MethodInfo.Invoke` s argumentmi prevedenými na typy parametrov."""

    def __init__(self, clr_type) -> None:
        self._type = clr_type

    def __getattr__(self, name: str):
        import System
        from System import Array, Object

        method = self._type.GetMethod(name)
        if method is None:
            raise AttributeError(name)
        params = [p.ParameterType for p in method.GetParameters()]
        # pythonnet do `object[]` vloží PyInt, ktorý reflexia na Int32/Int64 nepremení — boxuje sa ručne
        boxers = {"System.Int32": System.Int32, "System.Int64": System.Int64, "System.Double": System.Double,
                  "System.Boolean": System.Boolean, "System.String": System.String}

        def call(*args):
            assert len(args) == len(params), (name, len(args), len(params))
            boxed = Array[Object](len(args))
            for i, (a, t) in enumerate(zip(args, params)):
                boxed[i] = boxers[t.FullName](a) if t.FullName in boxers and a is not None else a
            return method.Invoke(None, boxed)

        return call


@pytest.fixture(scope="module")
def static_host():
    from tradebot.adapters.csharp import bridge

    try:
        bridge._load_clr()
    except bridge.BridgeError as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")
    from System import AppDomain

    for asm in AppDomain.CurrentDomain.GetAssemblies():
        if asm.GetName().Name == "TradeBot":
            t = asm.GetType("StaticHost")
            assert t is not None and t.Namespace is None, "StaticHost musí byť v globálnom namespace (MQL5 iný nevidí)"
            return _Reflected(t)
    pytest.fail("TradeBot.dll nie je načítaná")


def _instrument_json(inst) -> str:
    return json.dumps({
        "symbol": inst.symbol, "venue": inst.venue, "tick_size": inst.tick_size,
        "point_value": inst.point_value, "qty_step": inst.qty_step, "min_qty": inst.min_qty,
        "has_real_volume": inst.has_real_volume,
    })


def test_verzia_strategie_a_chyba_bez_vynimky(static_host):
    # docs/LIVE.md: Spool* (2), slot v id inštancie (3), SpoolMinute (4), EodDue (5), DailyStop* (6),
    # ochrana účtu V2 U1/U2 (7); EA kontroluje 7
    assert static_host.Version() == 7
    assert {"ibsnet", "orbnet"} <= set(static_host.Strategies().split(","))
    # chyba nesmie letieť cez hranicu .NET -> MQL5 ako výnimka: -1 a text v LastError
    inst = '{"symbol":"X","venue":"mt5","tick_size":0.25,"point_value":2.0,"qty_step":1,"min_qty":1}'
    assert static_host.Create("neexistuje", "{}", inst, 3) == -1
    assert "neexistuje" in static_host.LastError()
    assert static_host.Create("ibsnet", "{}", "{}", 3) == -1      # chýba tick_size
    assert "KeyNotFound" in static_host.LastError()
    assert static_host.OnBar(999, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, False, "") == ""
    assert "999" in static_host.LastError()


def test_fasada_da_to_iste_co_most_do_freqtrade(static_host):
    from tester import ninjatrader as nt
    from tradebot.adapters.freqtrade.runner import EngineRunner

    try:
        inst, base = nt._frame("btcusdt_binance", "2026-08-24", "2026-08-31")
    except SystemExit as exc:
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    spec = get_spec("ibsnet")
    cfg, _ = load_profile(TEST_PROFILES_DIR / "ibsnet" / "configs" / "golden_binance_btcusdt_3m.json", strategy="ibsnet")

    def bars(tf_minutes: int) -> list[Bar]:
        df = base if tf_minutes == 1 else resample_ohlcv(base, tf_minutes)
        ts = (df["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).tolist()
        return [Bar(int(t), float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume))
                for t, r in zip(ts, df.itertuples(index=False))]

    # referencia: most (EngineHost) s oknom HTF poskladaným v Pythone
    runner = EngineRunner(cfg, inst, 3, spec=spec)
    assert runner.htf is not None

    h = static_host.Create("ibsnet", json.dumps(cfg.to_dict()), _instrument_json(inst), 3)
    assert h > 0, static_host.LastError()
    try:
        facade_htf = static_host.HtfTfMinutes(h)
        assert facade_htf > 0
        assert static_host.RequiredHistory(h) == runner.engine.required_history

        chart, htf = bars(3), bars(facade_htf)
        for b in htf:
            runner.htf.feed(b)
        htf_ms = facade_htf * 60_000
        j = 0
        seen_orders = seen_events = 0
        for b in chart:
            # EA: HTF bary uzavreté najneskôr s otvorením baru grafu idú pred ním
            while j < len(htf) and htf[j].time + htf_ms <= b.time:
                assert static_host.FeedHtf(h, htf[j].time, htf[j].open, htf[j].high, htf[j].low, htf[j].close, htf[j].volume) == 1
                j += 1
            raw = static_host.OnBar(h, b.time, b.open, b.high, b.low, b.close, b.volume, 0.0, False, "")
            assert raw, static_host.LastError()
            out = json.loads(raw)
            ref = runner.engine.on_bar(b, runner.htf.window_for(b.time), None)

            got_orders = [(o["id"], o["a"], o.get("p") and (o["p"]["e"], o["p"]["sl"], o["p"]["tp"], o["p"]["q"]))
                          for o in out.get("o", [])]
            ref_orders = [(o.order_id, o.action.name.lower(),
                           o.plan and (o.plan.entry, o.plan.stop_loss, o.plan.take_profit, o.plan.qty))
                          for o in ref.orders]
            assert got_orders == ref_orders, b.time
            got_events = [(e["z"], e["f"], e["to"]) for e in out.get("e", [])]
            ref_events = [(e.zone_uid, e.from_state, e.to_state) for e in ref.events]
            assert got_events == ref_events, b.time
            seen_orders += len(got_orders)
            seen_events += len(got_events)
        assert seen_orders > 0 and seen_events > 0
        assert json.loads(static_host.Stats(h)) == runner.engine.stats()
    finally:
        static_host.Destroy(h)


# ---------------------------------------------------------------------------------------- #
# Live telemetria (docs/LIVE.md): `Spool*` cez reflexiu, riadky musia prejsť `schema.validate`
# ---------------------------------------------------------------------------------------- #

_INST = '{"symbol":"NAS100.cash","venue":"mt5","tick_size":0.25,"point_value":2.0,"qty_step":1,"min_qty":1,"has_real_volume":false}'


def _feed_bars(static_host, h: int, n: int, ready: bool) -> None:
    t0 = 1_790_000_000_000
    for i in range(n):
        px = 20000.0 + i
        raw = static_host.OnBar(h, t0 + i * 180_000, px, px + 5, px - 5, px + 1, 100.0 + i, 0.0, False, "")
        assert raw, static_host.LastError()
        assert static_host.SpoolBar(h, ready) == 1, static_host.LastError()


def test_spool_zapise_platne_udalosti(static_host, tmp_path):
    from tradebot.live import schema

    h = static_host.Create("ibsnet", "{}", _INST, 3)
    assert h > 0, static_host.LastError()
    try:
        # pred prvým barom nie je čo písať – 0, nie chyba
        assert static_host.SpoolBar(h, True) == 0
        assert static_host.SpoolOpen(h, str(tmp_path), "mt5", "5012345-Demo Server", "NAS100.cash", "nas100_dukas_3m", False) == 1, \
            static_host.LastError()
        path = static_host.SpoolPath(h)
        assert path
        instance = schema.instance_id("mt5", "5012345-Demo Server", "NAS100.cash", 3, "ibsnet")
        assert instance == "mt5_5012345-Demo-Server_NAS100.cash_3m_ibsnet"
        assert (tmp_path / instance).is_dir()
        assert str(tmp_path / instance) in path and path.endswith(".jsonl")

        _feed_bars(static_host, h, 3, False)
        assert static_host.SpoolRealtime(h, True) == 1
        _feed_bars(static_host, h, 2, True)
        # bid/ask a čas kotácie v ms ide k ďalšiemu fillu; bid/ask <= 0 kurz zabudne
        assert static_host.SpoolQuote(h, 20000.75, 20001.25, 1_790_000_600_480) == 1, static_host.LastError()
        assert static_host.SpoolFill(h, 1_790_000_600_500, "L-1", True, "", 20001.25, 1.0, True) == 1, static_host.LastError()
        assert static_host.SpoolQuote(h, 0.0, 20011.5, 1_790_000_700_400) == 1
        # trailing posunul SL: order/modify, tp=0 -> null (MQL nemá nullable)
        assert static_host.SpoolModify(h, 1_790_000_720_000, "L-1", 20005.5, 0.0, "trailing", True) == 1, static_host.LastError()
        assert static_host.SpoolFill(h, 1_790_000_700_500, "L-1", False, "sltp", 20011.25, 1.0, True) == 1
        assert static_host.SpoolNote(h, "warn", "bar prisiel neskoro") == 1
        assert static_host.SpoolClose(h, "deinit") == 1, static_host.LastError()
        assert static_host.SpoolPath(h) == ""
        # po zatvorení je všetko no-op (0), engine ide ďalej
        assert static_host.SpoolBar(h, True) == 0
        assert static_host.OnBar(h, 1_790_001_000_000, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, False, "")
    finally:
        static_host.Destroy(h)

    lines = (tmp_path / instance / path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]).read_text(encoding="utf-8").splitlines()
    events = [schema.parse_line(line) for line in lines]          # každý riadok musí byť platný
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    hello = events[0]
    assert hello["k"] == "hello" and hello["schema"] == 1 and hello["platform"] == "mt5"
    assert hello["account"] == "5012345-Demo Server" and hello["symbol"] == "NAS100.cash" and hello["tf"] == 3
    assert hello["strategy"] == "ibsnet" and hello["profile"] == "nas100_dukas_3m" and hello["tester"] is False
    assert len(hello["session"]) == 8 and hello["host"]
    assert isinstance(hello["config"], dict)
    assert hello["instrument"] == json.loads(_INST)
    assert path.endswith("_" + hello["session"] + ".jsonl")
    kinds = [e["k"] for e in events]
    assert kinds.count("bar") == 5 and {"fill", "note", "stat", "bye"} <= set(kinds)
    assert kinds[-1] == "bye" and kinds[-2] == "stat" and events[-1]["reason"] == "deinit"
    bars = [e for e in events if e["k"] == "bar"]
    assert [b["ready"] for b in bars] == [False] * 3 + [True] * 2
    assert bars[0]["bt"] == 1_790_000_000_000 and bars[0]["o"] == 20000.0 and "mb" in bars[0]
    fills = [e for e in events if e["k"] == "fill"]
    assert [(f["side"], f["exit"], f["id"]) for f in fills] == [("in", "", "L-1"), ("out", "sltp", "L-1")]
    assert (fills[0]["bid"], fills[0]["ask"], fills[0]["qt"], fills[0]["ft"]) == (20000.75, 20001.25, 1_790_000_600_480, 1_790_000_600_500)
    assert "bid" not in fills[1] and "ask" not in fills[1] and "qt" not in fills[1]
    mods = [e for e in events if e["k"] == "order" and e["a"] == "modify"]
    assert len(mods) == 1
    mod = mods[0]
    assert mod["id"] == "L-1" and mod["bt"] == 1_790_000_720_000 and mod["ready"] is True and mod["r"] == "trailing"
    assert mod["p"] == {"sl": 20005.5, "tp": None}
    assert events.index(mod) < events.index(next(e for e in events if e["k"] == "fill" and e["side"] == "out"))
    with pytest.raises(schema.SchemaError):
        schema.validate(dict(mod, a="move"))                        # neznáma akcia orderu sa odmietne
    note = next(e for e in events if e["k"] == "note")
    assert note["level"] == "warn" and "neskoro" in note["text"]
    stat = next(e for e in events if e["k"] == "stat")
    assert isinstance(stat["stats"], dict) and "max_daily_wins" in stat["stats"]
    assert all(isinstance(e["t"], int) and e["t"] > 1_700_000_000_000 for e in events)


def test_spool_minute_m1(static_host, tmp_path):
    """1m bary symbolu (`SpoolMinute`, docs/LIVE.md): platný riadok `m1` s časom otvorenia a OHLCV, číslovaný
    `seq` bez diery; bez spoolu no-op (0), do `bars` pingu sa nepočíta."""
    from tradebot.live import schema

    h = static_host.Create("ibsnet", "{}", _INST, 3)
    assert h > 0, static_host.LastError()
    try:
        assert static_host.SpoolMinute(h, 1_790_000_000_000, 1.0, 2.0, 0.5, 1.5, 7.0) == 0
        assert static_host.SpoolOpen(h, str(tmp_path), "mt5", "acc", "NAS100", "p", False) == 1, static_host.LastError()
        path = static_host.SpoolPath(h)
        for i in range(3):
            assert static_host.SpoolMinute(h, 1_790_000_000_000 + i * 60_000, 20000.0 + i, 20002.0 + i, 19999.0 + i,
                                           20001.0 + i, 10.0 + i) == 1, static_host.LastError()
        # so spreadom (sklad spreadu, tester.spread): v cene; <= 0 = neznáme, pole chýba
        assert static_host.SpoolMinuteSpread(h, 1_790_000_180_000, 20003.0, 20005.0, 20002.0, 20004.0, 13.0,
                                             0.5, 0.75, 0.0) == 1, static_host.LastError()
        assert static_host.SpoolClose(h, "deinit") == 1
    finally:
        static_host.Destroy(h)
    instance = schema.instance_id("mt5", "acc", "NAS100", 3, "ibsnet")
    lines = (tmp_path / instance / path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]).read_text(encoding="utf-8").splitlines()
    events = [schema.parse_line(line) for line in lines]
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    m1 = [e for e in events if e["k"] == "m1"]
    assert [(e["bt"], e["o"], e["h"], e["l"], e["c"], e["v"]) for e in m1[:3]] == [
        (1_790_000_000_000 + i * 60_000, 20000.0 + i, 20002.0 + i, 19999.0 + i, 20001.0 + i, 10.0 + i) for i in range(3)]
    assert all("sp" not in e for e in m1[:3])
    assert (m1[3]["bt"], m1[3]["sp"], m1[3]["spa"], "spx" in m1[3]) == (1_790_000_180_000, 0.5, 0.75, False)
    with pytest.raises(schema.SchemaError):
        schema.validate({"seq": 1, "t": 1, "k": "m1", "bt": 1, "o": 1, "h": 1, "l": 1, "c": 1})   # bez v


def test_control_instancia_a_udalost(static_host, tmp_path):
    """Fáza 2 (docs/LIVE.md): EA hľadá control súbor podľa id inštancie — `InstanceId` bez spoolu a
    `SpoolInstance` so spoolom musia dať to isté, čo `schema.instance_id`; `SpoolControl` píše platnú udalosť."""
    from tradebot.live import schema

    expected = schema.instance_id("mt5", "1514750898-FTMO-Demo", "US100.cash", 1, "ibsnet")
    assert expected == "mt5_1514750898-FTMO-Demo_US100.cash_1m_ibsnet"
    assert static_host.InstanceId("mt5", "1514750898-FTMO-Demo", "US100.cash", 1, "ibsnet") == expected

    h = static_host.Create("ibsnet", "{}", _INST, 1)
    assert h > 0, static_host.LastError()
    try:
        assert static_host.SpoolInstance(h) == ""                          # bez spoolu prázdne (EA použije InstanceId)
        assert static_host.SpoolControl(h, "paused", "x", "control") == 0  # bez spoolu no-op, nie chyba
        assert static_host.SpoolOpen(h, str(tmp_path), "mt5", "1514750898-FTMO-Demo", "US100.cash", "multicharts_mnq_3m", False) == 1, \
            static_host.LastError()
        assert static_host.SpoolInstance(h) == expected
        path = static_host.SpoolPath(h)
        assert static_host.SpoolControl(h, "enabled", "multicharts_mnq_3m", "default") == 1, static_host.LastError()
        assert static_host.SpoolControl(h, "paused", "multicharts_mnq_3m", "control") == 1
        assert static_host.SpoolControl(h, "flatten", "golden_binance_btcusdt_3m", "pending") == 1
        assert static_host.SpoolClose(h, "profile") == 1
    finally:
        static_host.Destroy(h)

    lines = (tmp_path / expected / path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]).read_text(encoding="utf-8").splitlines()
    events = [schema.parse_line(line) for line in lines]
    controls = [e for e in events if e["k"] == "control"]
    assert [(c["mode"], c["profile"], c["source"]) for c in controls] == [
        ("enabled", "multicharts_mnq_3m", "default"),
        ("paused", "multicharts_mnq_3m", "control"),
        ("flatten", "golden_binance_btcusdt_3m", "pending"),
    ]
    assert events[-1]["k"] == "bye" and events[-1]["reason"] == "profile"
    with pytest.raises(schema.SchemaError):
        schema.validate({"seq": 1, "t": 1, "k": "control", "mode": "stop"})


def test_slot_v_id_instancie(static_host, tmp_path):
    """Slot nasadenia (docs/MT5.md, „Viac stratégií na jednom serveri“): `InstanceIdSlot` a spool otvorený cez
    `SpoolOpenSlot` dávajú to isté, čo `schema.instance_id(..., slot)`; prázdny slot = id bez neho."""
    from tradebot.live import schema

    expected = schema.instance_id("mt5", "1514750898-FTMO-Demo", "US100.cash", 3, "orbnet", "b")
    assert expected == "mt5_1514750898-FTMO-Demo_US100.cash_3m_orbnet_b"
    assert static_host.InstanceIdSlot("mt5", "1514750898-FTMO-Demo", "US100.cash", 3, "orbnet", "b") == expected
    assert static_host.InstanceIdSlot("mt5", "1514750898-FTMO-Demo", "US100.cash", 3, "orbnet", "") == \
        static_host.InstanceId("mt5", "1514750898-FTMO-Demo", "US100.cash", 3, "orbnet")
    h = static_host.Create("orbnet", "{}", _INST, 3)
    assert h > 0, static_host.LastError()
    try:
        assert static_host.SpoolOpenSlot(h, str(tmp_path), "mt5", "1514750898-FTMO-Demo", "US100.cash", "p", False, "b") == 1, \
            static_host.LastError()
        assert static_host.SpoolInstance(h) == expected
    finally:
        static_host.Destroy(h)
    assert (tmp_path / expected).is_dir()


def test_spool_zly_koren_nezhodi_engine(static_host, tmp_path):
    blocker = tmp_path / "subor.txt"
    blocker.write_text("nie som adresar", encoding="utf-8")
    h = static_host.Create("ibsnet", "{}", _INST, 3)
    assert h > 0, static_host.LastError()
    try:
        assert static_host.SpoolOpen(h, str(blocker / "spool"), "mt5", "acc", "NAS100", "p", False) == -1
        assert static_host.LastError()
        assert static_host.SpoolPath(h) == ""
        assert static_host.SpoolBar(h, True) == 0            # spool nie je, nie chyba
        raw = static_host.OnBar(h, 1_790_000_000_000, 1.0, 2.0, 0.5, 1.5, 10.0, 0.0, False, "")
        assert raw and json.loads(raw) is not None
        assert static_host.SpoolClose(h, "x") == 0
    finally:
        static_host.Destroy(h)


def test_ping_hb_necisluje_seq_a_v_testeri_nie_je(static_host, tmp_path):
    """Ping (docs/LIVE.md, „Ping“): `SpoolHeartbeat` aj časovač `LiveSpool` píšu platný `hb` s posledným
    `seq` (bez diery), `bars`/`lb`/`mode`; v Testeri časovač nebeží."""
    import time

    from tradebot.live import schema

    h = static_host.Create("ibsnet", "{}", _INST, 3)
    assert h > 0, static_host.LastError()
    try:
        assert static_host.SpoolHeartbeat(h) == 0                          # bez spoolu no-op
        assert static_host.SpoolOpen(h, str(tmp_path), "mt5", "5012345-Demo Server", "NAS100.cash", "p", False) == 1, \
            static_host.LastError()
        path = static_host.SpoolPath(h)
        assert static_host.SpoolHeartbeat(h) == 1, static_host.LastError()   # hneď po hello: seq 1, žiadny bar
        _feed_bars(static_host, h, 2, True)
        assert static_host.SpoolControl(h, "paused", "p", "control") == 1
        assert static_host.SpoolHeartbeat(h) == 1
        assert static_host.SpoolNote(h, "info", "po pingu") == 1
        # hb sa flushuje hneď — agent ho vidí, aj keď spool nie je v realtime
        hb_lines = [x for x in open(path, encoding="utf-8").read().splitlines() if '"k":"hb"' in x]
        assert len(hb_lines) == 2
        assert static_host.SpoolClose(h, "deinit") == 1
    finally:
        static_host.Destroy(h)

    events = [schema.parse_line(x) for x in open(path, encoding="utf-8").read().splitlines()]
    cisla = [e["seq"] for e in events if e["k"] != "hb"]
    assert cisla == list(range(1, len(cisla) + 1))                       # hb dieru nespraví
    hb = [e for e in events if e["k"] == "hb"]
    assert hb[0]["seq"] == 1 and hb[0]["bars"] == 0 and hb[0]["lb"] == 0 and "mode" not in hb[0]
    po = events[events.index(hb[1]) - 1]
    assert hb[1]["seq"] == po["seq"] and po["k"] == "control"
    assert hb[1]["bars"] == 2 and hb[1]["lb"] == 1_790_000_180_000 and hb[1]["mode"] == "paused"
    assert events[events.index(hb[1]) + 1]["seq"] == hb[1]["seq"] + 1

    # časovač: krátky interval priamo na LiveSpool; Tester ho nespustí
    from System.Collections.Generic import Dictionary
    from System import Object, String
    from TradeBot.Core import LiveSpool

    def otvor(root, tester):
        sp = LiveSpool(str(root), "mt5", "A", "S", 3, "ibsnet", "p", tester, Dictionary[String, Object](), None)
        assert not sp.Broken, sp.LastError
        return sp

    zivy, tst = otvor(tmp_path / "zivy", False), otvor(tmp_path / "tester", True)
    assert zivy.HeartbeatMs == 60000
    zivy.HeartbeatMs = 40
    tst.HeartbeatMs = 40
    koniec = time.time() + 5
    while time.time() < koniec and open(zivy.Path, encoding="utf-8").read().count('"k":"hb"') < 2:
        time.sleep(0.05)
    zivy.Close("x")
    tst.Close("x")
    zive = [schema.parse_line(x) for x in open(zivy.Path, encoding="utf-8")]
    assert sum(e["k"] == "hb" for e in zive) >= 2 and all(e["seq"] == 1 for e in zive if e["k"] == "hb")
    assert zive[-1]["k"] == "bye" and zive[-1]["seq"] == 2               # hello 1, bye 2 — pingy nečíslujú
    assert '"k":"hb"' not in open(tst.Path, encoding="utf-8").read()     # v Testeri žiadny ping


def test_pozicia_u_brokera_ide_do_pingu_len_pri_zmene(static_host, tmp_path):
    """`SpoolBroker` (MT5 EA, v NinjaTrader AddOne `LiveSpool.Broker`): pozícia u brokera ide do `hb` (`pos`,
    `pos_px`, `pos_of`) — nová hneď, rovnaká znova nie; ďalší ping (časovač) ju nesie tiež. Webapp z nej vidí,
    či pozícia u brokera naozaj je, nie len odhad z fillov."""
    from tradebot.live import schema

    h = static_host.Create("ibsnet", "{}", _INST, 3)
    assert h > 0, static_host.LastError()
    try:
        assert static_host.SpoolBroker(h, -1.0, 29445.5, "magic") == 0          # bez spoolu no-op
        assert static_host.SpoolOpen(h, str(tmp_path), "mt5", "5012345-Demo Server", "NAS100.cash", "p", False) == 1, \
            static_host.LastError()
        path = static_host.SpoolPath(h)
        assert static_host.SpoolBroker(h, -1.0, 29445.5, "magic") == 1, static_host.LastError()
        assert static_host.SpoolBroker(h, -1.0, 29445.5, "magic") == 1          # bez zmeny: žiadny nový riadok
        assert static_host.SpoolBroker(h, 0.0, 0.0, "magic") == 1
        assert static_host.SpoolHeartbeat(h) == 1
        assert static_host.SpoolClose(h, "deinit") == 1
    finally:
        static_host.Destroy(h)

    hb = [schema.parse_line(x) for x in open(path, encoding="utf-8").read().splitlines() if '"k":"hb"' in x]
    assert [(e["pos"], e["pos_px"], e["pos_of"]) for e in hb] == [(-1.0, 29445.5, "magic"), (0.0, 0.0, "magic"), (0.0, 0.0, "magic")]


def test_eod_podla_hodin(static_host):
    """`EodDue` (audit N-LIVE-7): engine s koncom dna chce byt od 15:58:30 do 18:00 New York flat aj bez baru;
    engine bez EOD nikdy. Letný aj zimný čas: vždy hodiny NY."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    def ms(y, mo, d, hh, mm, ss=0):
        return int(datetime(y, mo, d, hh, mm, ss, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)

    eod = static_host.Create("noaneteod", "{}", _INST, 3)
    plain = static_host.Create("noanet", "{}", _INST, 3)
    assert eod > 0 and plain > 0, static_host.LastError()
    try:
        for day in ((2026, 7, 15), (2026, 12, 15)):
            assert static_host.EodDue(eod, ms(*day, 15, 58, 29)) == 0
            assert static_host.EodDue(eod, ms(*day, 15, 58, 30)) == 1
            assert static_host.EodDue(eod, ms(*day, 17, 59, 59)) == 1
            assert static_host.EodDue(eod, ms(*day, 18, 0, 0)) == 0
            assert static_host.EodDue(plain, ms(*day, 16, 0, 0)) == 0
        assert static_host.EodDue(987654, 0) == -1 and static_host.LastError()
    finally:
        static_host.Destroy(eod)
        static_host.Destroy(plain)


def test_kontrola_pred_startom_hlasi_koniec_kalendara(static_host):
    """`Preflight` (audit 9. 11. 2026, vylepšenie 6): engine so zoznamom termínov povie pri živom štarte, že mu
    kalendár končí — inak by typ správy ticho prestal obchodovať (M-CORE-3). Engine bez kontroly nehlási nič."""
    from datetime import datetime, timezone

    def ms(y, mo, d):
        return int(datetime(y, mo, d, tzinfo=timezone.utc).timestamp() * 1000)

    news = static_host.Create("spravynet", "{}", _INST, 1)
    plain = static_host.Create("noanet", "{}", _INST, 3)
    assert news > 0 and plain > 0, static_host.LastError()
    try:
        assert static_host.Preflight(news, ms(2022, 6, 1)) == ""          # kalendár má pred sebou roky
        neskoro = static_host.Preflight(news, ms(2035, 1, 1))
        assert neskoro and all("skoncil" in riadok for riadok in neskoro.split("\n"))
        assert static_host.Preflight(plain, ms(2035, 1, 1)) == ""
        assert "987654" in static_host.Preflight(987654, 0)                # chyba ako text, nie výnimka
    finally:
        static_host.Destroy(news)
        static_host.Destroy(plain)


def test_rozbity_spool_sa_otvori_znova(static_host, tmp_path):
    """Chyba zápisu spoolu nevypne telemetriu navždy (audit N-LIVE-19): po `ReopenSeconds` ďalšie volanie
    otvorí nový súbor tej istej session s `hello` a `note warn`, seq pokračuje."""
    from TradeBot.Core import LiveSpool
    from tradebot.live import schema

    blocker = tmp_path / "spool"
    blocker.write_text("zatial nie som adresar", encoding="utf-8")
    old = LiveSpool.ReopenSeconds
    LiveSpool.ReopenSeconds = 0
    try:
        sp = LiveSpool(str(blocker), "mt5", "acc", "NAS100", 3, "ibsnet", "p", False, None, None)
        assert sp.Broken and sp.LastError
        blocker.unlink()
        sp.Note("info", "po obnove")
        assert not sp.Broken, sp.LastError
        sp.Close("deinit")
    finally:
        LiveSpool.ReopenSeconds = old
    files = list((blocker / sp.Instance).glob("*.jsonl"))
    assert len(files) == 1
    events = [schema.parse_line(line) for line in files[0].read_text(encoding="utf-8").splitlines()]
    kinds = [e["k"] for e in events]
    assert kinds[0] == "hello" and kinds[1] == "note" and events[1]["level"] == "warn"
    assert any(e["k"] == "note" and e.get("text") == "po obnove" for e in events)


def test_restart_nezapise_znova_m1_ani_historicke_bary(static_host, tmp_path):
    """Po reštarte inštancia prehrá predhistóriu znova — `m1` a historické bary (`ready:false`), ktoré predošlý
    beh už zapísal, nový beh do spoolu nedá (bary len pri tom istom profile a configu). Zámery, prechody
    a kresby idú ďalej, `seq` je bez dier. V Testeri sa nič nevynecháva."""
    from System import Object, String
    from System.Collections.Generic import Dictionary

    from TradeBot.Core import Bar as CsBar
    from TradeBot.Core import LiveSpool
    from tradebot.live import schema

    T0, M = 1_790_000_000_000, 60_000

    def beh(profile, n_bars, n_live, n_min, tester=False):
        sp = LiveSpool(str(tmp_path), "mt5", "A", "S", 3, "ibsnet", profile, tester, Dictionary[String, Object](), None)
        assert not sp.Broken, sp.LastError
        for k in range(n_min):
            sp.Minute(T0 + k * M, 1.0, 2.0, 0.5, 1.5, 1.0)
        for k in range(n_bars):
            sp.Bar(CsBar(T0 + k * 3 * M, 1.0, 2.0, 0.5, 1.5, 1.0), None, k >= n_bars - n_live, 0)
        sp.Close("deinit")
        ev = [schema.parse_line(x) for x in open(sp.Path, encoding="utf-8").read().splitlines()]
        assert [e["seq"] for e in ev] == list(range(1, len(ev) + 1))
        return sp, [e["bt"] for e in ev if e["k"] == "bar"], [e["bt"] for e in ev if e["k"] == "m1"]

    a, bary, m1 = beh("p", 6, 1, 10)
    assert len(bary) == 6 and len(m1) == 10 and a.SkippedBars == 0
    import time as _t
    _t.sleep(1.1)                                              # iný názov súboru (sekundy v čase štartu)
    b, bary, m1 = beh("p", 8, 1, 12)                           # prehrá 7 historických + 1 živý, 12 minút
    assert bary == [T0 + k * 3 * M for k in (6, 7)]            # historický bar 6 (za predošlým) a živý 7
    assert m1 == [T0 + k * M for k in (10, 11)] and b.SkippedBars == 6 and b.SkippedMinutes == 10
    _t.sleep(1.1)
    c, bary, m1 = beh("iny", 8, 1, 12)                         # iný profil: bary všetky, m1 nie
    assert len(bary) == 8 and m1 == [] and c.SkippedBars == 0 and c.SkippedMinutes == 12
    _t.sleep(1.1)
    d, bary, m1 = beh("p", 8, 1, 12, tester=True)              # Tester: všetko
    assert len(bary) == 8 and len(m1) == 12


# -- denný stop účtu (docs/DAILY_STOP.md) ------------------------------------------------------------ #

def _utc_ms(text: str) -> int:
    from datetime import datetime, timezone
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def _reset_daily_stop() -> None:
    from System import AppDomain

    for asm in AppDomain.CurrentDomain.GetAssemblies():
        if asm.GetName().Name == "TradeBot":
            asm.GetType("TradeBot.Core.DailyStop").GetMethod("ResetShared").Invoke(None, None)
            return


def test_denny_stop_zastavi_do_noveho_dna(static_host, tmp_path):
    _reset_daily_stop()
    d, acc, ny = str(tmp_path), "mt5-1-Demo", "America/New_York"
    check = lambda when, eq, pct=4.0: static_host.DailyStopCheck(d, acc, pct, ny, "18:00", _utc_ms(when), eq)
    assert check("2026-11-25T15:00:00", 100_000.0) == 0      # 10:00 NY, základ dňa 24. 11. (od 18:00 NY)
    assert check("2026-11-25T15:30:00", 96_001.0) == 0
    assert check("2026-11-25T16:00:00", 0.0) == 0             # terminál bez equity stav nemení
    assert check("2026-11-25T16:00:01", 96_000.0) == 1        # presne -4 %
    assert check("2026-11-25T16:30:00", 99_000.0) == 1        # zotavenie nič nemení - zastavené do konca dňa
    text = static_host.DailyStopText(d, acc, 4.0, ny, "18:00")
    assert "ZASTAVENE" in text and "96000.00" in text and "den 20261124" in text
    state = json.loads((tmp_path / "dailystop_mt5-1-Demo_America-New-York_1800.json").read_text(encoding="utf-8"))
    assert state["day"] == "20261124" and state["base"] == 100_000.0 and state["stopped"] is True
    assert check("2026-11-25T22:59:59", 99_000.0) == 1        # 17:59:59 NY
    assert check("2026-11-25T23:00:00", 95_000.0) == 0        # 18:00 NY: nový deň, nový základ
    assert check("2026-11-26T12:00:00", 91_201.0) == 0
    assert check("2026-11-26T12:00:01", 91_200.0) == 1


def test_denny_stop_spolocny_pre_ucet_a_cez_restart(static_host, tmp_path):
    _reset_daily_stop()
    d, ny = str(tmp_path), "America/New_York"
    t = _utc_ms("2026-11-25T15:00:00")
    # dve inštancie na jednom účte: prísnejšia (-2 %) zastaví účet aj druhej (-4 %)
    assert static_host.DailyStopCheck(d, "nt-Sim101", 4.0, ny, "18:00", t, 50_000.0) == 0
    assert static_host.DailyStopCheck(d, "nt-Sim101", 2.0, ny, "18:00", t + 1000, 49_000.0) == 1
    assert static_host.DailyStopCheck(d, "nt-Sim101", 4.0, ny, "18:00", t + 2000, 49_500.0) == 1
    assert "prisnejsie nastavenie -2 %" in static_host.DailyStopText(d, "nt-Sim101", 4.0, ny, "18:00")
    # iný účet nič nezdieľa
    assert static_host.DailyStopCheck(d, "nt-Sim102", 4.0, ny, "18:00", t, 49_000.0) == 0
    # reštart platformy (nový proces = prázdna pamäť): zastavenie aj základ prídu zo súboru
    _reset_daily_stop()
    assert static_host.DailyStopCheck(d, "nt-Sim101", 4.0, ny, "18:00", t + 60_000, 49_900.0) == 1
    _reset_daily_stop()
    assert static_host.DailyStopCheck(d, "nt-Sim102", 4.0, ny, "18:00", t + 60_000, 47_100.0) == 0   # základ 49 000
    assert static_host.DailyStopCheck(d, "nt-Sim102", 4.0, ny, "18:00", t + 61_000, 47_040.0) == 1


def test_denny_stop_hranica_dna_a_zle_nastavenie(static_host, tmp_path):
    _reset_daily_stop()
    # FTMO: deň od polnoci Europe/Prague (zima UTC+1); tester bez adresára = len pamäť, žiadny súbor
    check = lambda when, eq: static_host.DailyStopCheck("", "mt5-tester", 5.0, "Europe/Prague", "00:00", _utc_ms(when), eq)
    assert check("2026-11-25T10:00:00", 10_000.0) == 0
    assert check("2026-11-25T22:59:00", 9_500.0) == 1          # 23:59 Praha
    assert check("2026-11-25T23:00:00", 9_500.0) == 0          # 00:00 Praha - nový deň
    assert not list(tmp_path.iterdir())
    for pct, zone, time, why in [(0.0, "UTC", "18:00", "percento"), (4.0, "Mars/Olymp", "18:00", "pasmo"),
                                 (4.0, "UTC", "25:00", "HH:MM"), (4.0, "UTC", "18", "HH:MM")]:
        assert static_host.DailyStopCheck(str(tmp_path), "a", pct, zone, time, 0, 1.0) == -1
        assert why in static_host.LastError()
        assert static_host.DailyStopText(str(tmp_path), "a", pct, zone, time) == ""


def test_denny_stop_v2_zaklad_max_balance_equity_a_reset_praha(static_host, tmp_path):
    """SMERNICA V2 U1: základ dňa = max(balance, equity), predvolene 00:00 Europe/Prague aj cez letný čas."""
    from System import AppDomain

    _reset_daily_stop()
    d, acc = str(tmp_path), "mt5-9-Demo"
    check = lambda when, eq, bal: static_host.DailyStopCheckBal(d, acc, 4.0, "Europe/Prague", "00:00", _utc_ms(when), eq, bal)
    # otvorená strata cez polnoc: equity 99 000, balance 100 000 -> základ 100 000, hranica 96 000
    assert check("2026-07-15T08:00:00", 99_000.0, 100_000.0) == 0
    assert check("2026-07-15T09:00:00", 96_001.0, 100_000.0) == 0
    assert check("2026-07-15T09:00:01", 96_000.0, 100_000.0) == 1
    # leto UTC+2: 21:59 UTC je 23:59 Praha (ten istý deň), 22:00 UTC je polnoc -> nový deň
    assert check("2026-07-15T21:59:00", 96_500.0, 97_000.0) == 1
    assert check("2026-07-15T22:00:00", 96_500.0, 97_000.0) == 0           # základ 97 000
    assert check("2026-07-16T10:00:00", 93_121.0, 97_000.0) == 0
    assert check("2026-07-16T10:00:01", 93_120.0, 97_000.0) == 1
    # po prechode na zimný čas (25. 10. 2026) je polnoc Praha 23:00 UTC
    assert check("2026-10-25T22:59:00", 99_000.0, 99_000.0) == 0
    assert check("2026-10-25T23:00:00", 99_000.0, 99_000.0) == 0
    text = static_host.DailyStopText(d, acc, 4.0, "Europe/Prague", "00:00")
    assert "den 20261026" in text and "zaklad 99000.00" in text
    asm = next(a for a in AppDomain.CurrentDomain.GetAssemblies() if a.GetName().Name == "TradeBot")
    t = asm.GetType("TradeBot.Core.DailyStopRule")
    assert t.GetField("DefaultZone").GetValue(None) == "Europe/Prague" and t.GetField("DefaultTime").GetValue(None) == "00:00"


def test_denny_stop_zametanie_uctu_raz_az_po_oneskoreni(static_host, tmp_path):
    _reset_daily_stop()
    d, acc, z = str(tmp_path), "mt5-7-Demo", "Europe/Prague"
    t0 = _utc_ms("2026-11-25T10:00:00")
    assert static_host.DailyStopCheckBal(d, acc, 4.0, z, "00:00", t0, 100_000.0, 100_000.0) == 0
    assert static_host.DailyStopSweepDue(d, acc, 4.0, z, "00:00", t0) == 0            # nezastavený účet
    assert static_host.DailyStopCheckBal(d, acc, 4.0, z, "00:00", t0 + 1000, 95_000.0, 100_000.0) == 1
    # vlastné pozície zatvárajú inštancie samy - zametanie účtu až po 10 s a potom najviac raz za 5 s v procese
    assert static_host.DailyStopSweepDue(d, acc, 4.0, z, "00:00", t0 + 5000) == 0
    assert static_host.DailyStopSweepDue(d, acc, 4.0, z, "00:00", t0 + 11_000) == 1
    assert static_host.DailyStopSweepDue(d, acc, 4.0, z, "00:00", t0 + 12_000) == 0     # iné EA v tom istom termináli
    assert static_host.DailyStopSweepDue(d, acc, 4.0, z, "00:00", t0 + 16_001) == 1


def test_sucasne_riziko_uctu_a_pozicia_bez_sl(static_host):
    """V2 U1.2/U1.3: súčet rizík do SL ≤ 1,5 % equity; pozícia bez SL > 5 s od fillu sa zavrie."""
    assert static_host.PositionRisk(20000.0, 19990.0, 2.0, 2.0) == pytest.approx(40.0)      # MNQ 10 b x 2 x 2 $
    assert static_host.PositionRisk(20000.0, 0.0, 2.0, 2.0) == -1                           # bez SL
    assert static_host.OpenRiskVerdict(1000.0, 499.0, 100_000.0, 1.5) == ""
    assert "1500.00" in static_host.OpenRiskVerdict(1000.0, 501.0, 100_000.0, 1.5)
    assert "bez SL" in static_host.OpenRiskVerdict(-1.0, 10.0, 100_000.0, 1.5)
    assert "nema SL" in static_host.OpenRiskVerdict(0.0, -1.0, 100_000.0, 1.5)
    assert static_host.OpenRiskVerdict(-1.0, -1.0, 100_000.0, 0.0) == ""                     # 0 = vypnuté
    assert static_host.StopOverdue(1_000, 5_999, False) == 0
    assert static_host.StopOverdue(1_000, 6_000, False) == 1
    assert static_host.StopOverdue(1_000, 60_000, True) == 0


def test_zamok_duplicity_skupiny_uctov(static_host, tmp_path):
    """V2 U1.4: tá istá stratégia s tým istým profilom na dvoch účtoch skupiny sa nespustí."""
    from System import String
    from TradeBot.Core import AccountGuard, DupLock

    assert AccountGuard.GroupOf("222", "mt5-222-S", "111, 222;333") == "grp-111,222"
    assert AccountGuard.GroupOf("999", "mt5-999-S", "111,222") == "mt5-999-S"
    path = DupLock.PathOf(str(tmp_path), "grp-111,222", "ibsentrynet", "ZAKLAD_MNQ")
    ok, other = DupLock.Claim(path, "mt5-111|T1", 1_000_000, String(""))
    assert ok
    ok, other = DupLock.Claim(path, "mt5-222|T2", 1_060_000, String(""))
    assert not ok and other == "mt5-111|T1"
    ok, _ = DupLock.Claim(path, "mt5-111|T1", 1_070_000, String(""))             # ten istý vlastník (reštart)
    assert ok
    ok, _ = DupLock.Claim(path, "mt5-222|T2", 1_070_000 + 120_000, String(""))   # zámok po páde vyprší
    assert ok
    name = path.replace("\\", "/").split("/")[-1]
    DupLock.Release(path, "mt5-111|T1")                                          # cudzí zámok sa neuvoľní
    assert (tmp_path / name).exists()
    DupLock.Release(path, "mt5-222|T2")
    assert not (tmp_path / name).exists()


def test_spool_ochrana_uctu_odmietnutie_a_fill_s_typom_prikazu(static_host, tmp_path):
    """V2 U1.6 a U2: riadky `account_guard`, `reject` a fill s typom príkazu, požadovanou cenou a kurzom pri odoslaní."""
    from tradebot.live import schema

    h = static_host.Create("ibsnet", "{}", _INST, 3)
    assert h > 0, static_host.LastError()
    try:
        assert static_host.SpoolOpen(h, str(tmp_path), "mt5", "77-Demo", "US100.cash", "p", False) == 1, static_host.LastError()
        path = static_host.SpoolPath(h)
        assert static_host.SpoolGuard(h, "daily_stop", "denny stop -4 %", 95_000.0, -1.0) == 1, static_host.LastError()
        assert static_host.SpoolGuard(h, "risk", "vstup L-1: sucasne riziko", -1.0, 1500.0) == 1
        assert static_host.SpoolQuote(h, 20000.0, 20002.0, 1_790_000_000_100) == 1
        assert static_host.SpoolReject(h, 1_790_000_000_200, "L-2", "10015", 19990.0, "Invalid price") == 1, static_host.LastError()
        assert static_host.SpoolFillEx(h, 1_790_000_000_300, "L-1", True, "", 20002.5, 1.0, True, "limit", 20002.0,
                                       19999.0, 20001.0, 1_790_000_000_050) == 1, static_host.LastError()
        assert static_host.SpoolFillEx(h, 1_790_000_100_000, "L-1", False, "Stop loss", 19989.0, 1.0, True, "sl", 19990.0,
                                       0.0, 0.0, 0) == 1
        assert static_host.SpoolClose(h, "deinit") == 1
    finally:
        static_host.Destroy(h)
    parts = path.replace("\\", "/").split("/")
    events = [schema.parse_line(x) for x in (tmp_path / parts[-2] / parts[-1]).read_text(encoding="utf-8").splitlines()]
    guards = [e for e in events if e["k"] == "account_guard"]
    assert [(g["what"], g.get("v"), g.get("lim")) for g in guards] == [("daily_stop", 95_000.0, None), ("risk", None, 1500.0)]
    rej = next(e for e in events if e["k"] == "reject")
    assert (rej["id"], rej["code"], rej["price"], rej["bid"], rej["ask"], rej["spr"]) == ("L-2", "10015", 19990.0, 20000.0, 20002.0, 2.0)
    fin, fout = [e for e in events if e["k"] == "fill"]
    assert (fin["ok"], fin["req"], fin["sb"], fin["sa"], fin["st"], fin["sspr"]) == ("limit", 20002.0, 19999.0, 20001.0, 1_790_000_000_050, 2.0)
    assert fin["price"] - fin["req"] == pytest.approx(0.5)                                     # sklz
    assert (fout["ok"], fout["req"]) == ("sl", 19990.0) and "sb" not in fout
