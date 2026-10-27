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
    assert static_host.Version() == 5      # docs/LIVE.md: Spool* (2), slot v id inštancie (3), SpoolMinute (4), EodDue (5); EA kontroluje 5
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
    cfg, _ = load_profile("golden_binance_btcusdt_3m", strategy="ibsnet")

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
        assert static_host.SpoolFill(h, 1_790_000_600_500, "L-1", True, "", 20001.25, 1.0, True) == 1, static_host.LastError()
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
        assert static_host.SpoolClose(h, "deinit") == 1
    finally:
        static_host.Destroy(h)
    instance = schema.instance_id("mt5", "acc", "NAS100", 3, "ibsnet")
    lines = (tmp_path / instance / path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]).read_text(encoding="utf-8").splitlines()
    events = [schema.parse_line(line) for line in lines]
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    m1 = [e for e in events if e["k"] == "m1"]
    assert [(e["bt"], e["o"], e["h"], e["l"], e["c"], e["v"]) for e in m1] == [
        (1_790_000_000_000 + i * 60_000, 20000.0 + i, 20002.0 + i, 19999.0 + i, 20001.0 + i, 10.0 + i) for i in range(3)]
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
