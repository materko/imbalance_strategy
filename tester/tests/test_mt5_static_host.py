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
    assert static_host.Version() == 2      # docs/LIVE.md: Spool* pribudli, EA kontroluje 2
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
    note = next(e for e in events if e["k"] == "note")
    assert note["level"] == "warn" and "neskoro" in note["text"]
    stat = next(e for e in events if e["k"] == "stat")
    assert isinstance(stat["stats"], dict) and "max_daily_wins" in stat["stats"]
    assert all(isinstance(e["t"], int) and e["t"] > 1_700_000_000_000 for e in events)


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
