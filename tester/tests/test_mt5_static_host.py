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
    assert static_host.Version() == 1
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
