"""Smerovanie príkazov (docs/ROUTING.md): stratégia v NinjaTraderi, ordery v MT5 exekútore.

Master (NinjaTrader AddOn) volá `TradeBot.Core.BridgeMaster` priamo, exekútor (MQL5) len statickú fasádu
`StaticHost.Bridge*` — test ich volá presne tak, takže overuje to, čo uvidia obe platformy:

* prepočet cien (basis), SL/TP od fillu, objem podľa hodnoty bodu a termíny `OrderLife`;
* protokol: route.json, príkazy s `cid`, idempotencia cez reštart exekútora, udalosti späť, kurzor mastera;
* stav route z heartbeatu exekútora (`no_executor`, `stale`, `netting_unsupported` …);
* EOD obal dáva vstupom `life.close_at` = 15:58:30 New York.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from tester.tests.test_mt5_static_host import _Reflected

NY = ZoneInfo("America/New_York")
T0 = 1_790_000_000_000


@pytest.fixture(scope="module")
def clr():
    from tradebot.adapters.csharp import bridge

    try:
        bridge._load_clr()
    except bridge.BridgeError as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")
    import TradeBot.Core as core
    from System import AppDomain

    for asm in AppDomain.CurrentDomain.GetAssemblies():
        if asm.GetName().Name == "TradeBot":
            return core, _Reflected(asm.GetType("StaticHost"))
    pytest.fail("TradeBot.dll nie je načítaná")


def _spec(core, to: str, instance: str = "ninjatrader_Sim101_MNQ_3m_ibsnet"):
    s = core.RouteSpec()
    s.To, s.Instance, s.Deployment, s.Symbol = to, instance, "dep-1", "US100.cash"
    s.Magic, s.NtSymbol, s.NtPointValue, s.NtTick, s.Tf = 4711, "MNQ", 2.0, 0.25, 3
    return s


def _entry(core, oid: str = "L-1", life_close: int = 0):
    i = core.OrderIntent(core.OrderAction.Entry, oid, 7, "zone touch")
    i.Direction = core.Direction.Long
    i.Plan = core.TradePlan(core.Direction.Long, 20000.0, 19980.0, 20040.0, 1.0, 20.0, None)
    if life_close:
        i.Life = core.OrderLife()
        i.Life.CloseAtMs = life_close
    return i


def _hb(host, h, now, *, margin="hedging", connected=True, trade=True, symbol="US100.cash", mode=4, route=None):
    assert host.BridgeHbBegin(h, now, 5012345, "FTMO-Demo", margin, connected, trade, "test") == 1, host.LastError()
    assert host.BridgeHbSymbol(h, symbol, 0.01, 0.01, 0.01, 0.01, 100.0, mode, 20100.0, 20101.0) == 1
    if route:
        assert host.BridgeHbRoute(h, route[0], route[1], "") == 1
    assert host.BridgeHbWrite(h) == 1, host.LastError()


# --------------------------------------------------------------------------- #


def test_prepocet_cien_a_objemu(clr):
    _, host = clr
    # NT 20000, MT5 mid 20150.5 -> limitka 5 bodov pod trhom ostane 5 bodov pod trhom
    assert host.BridgeMapPrice(19995.0, 20000.0, 20150.5, 1.0, 0.01) == pytest.approx(20145.5)
    assert host.BridgeMapPrice(19995.13, 20000.0, 20150.5, 1.0, 0.25) == pytest.approx(20145.75)
    assert host.BridgeToNtPrice(20145.5, 20000.0, 20150.5, 1.0) == pytest.approx(19995.0)
    # SL/TP od skutočného fillu: plán vstup 20000, SL 19980 -> fill 20146.3 má SL o 20 nižšie
    assert host.BridgeReanchor(20146.3, 20000.0, 19980.0, 1.0, 0.01) == pytest.approx(20126.3)
    assert host.BridgeReanchor(20146.3, 20000.0, 20040.0, 1.0, 0.01) == pytest.approx(20186.3)

    # MNQ 2 $/bod, NAS100 tick 0.01 za 0.01 $ = 1 $/bod/lot -> 2 loty na kontrakt
    assert host.BridgeLots(1.0, 2.0, 1.0, 0.01, 0.01, 0.01, 0.01, 100.0, "value", 0.0) == pytest.approx(2.0)
    assert host.BridgeLots(3.0, 2.0, 1.0, 0.01, 0.01, 0.1, 0.1, 100.0, "value", 0.0) == pytest.approx(6.0)
    # nadol na krok, pod minimum 0 (odmietne sa), nad maximum maximum
    assert host.BridgeLots(1.0, 0.5, 1.0, 1.0, 0.1, 0.1, 0.1, 100.0, "value", 0.0) == pytest.approx(0.0)
    assert host.BridgeLots(1.0, 2.0, 1.0, 0.03, 0.01, 0.01, 0.01, 100.0, "value", 0.0) == pytest.approx(0.66)
    assert host.BridgeLots(100.0, 2.0, 1.0, 0.01, 0.01, 0.01, 0.01, 50.0, "value", 0.0) == pytest.approx(50.0)
    assert host.BridgeLots(2.0, 2.0, 1.0, 0.01, 0.01, 0.01, 0.01, 100.0, "fixed", 0.5) == pytest.approx(1.0)


def test_terminy_orderu(clr):
    _, host = clr
    g = 5000
    # close_at: čakajúci sa zruší, otvorený zavrie - až po odklade 5 s
    assert host.BridgeLifeAction(0, T0, 0, False, 0, T0 + g - 1) == ""
    assert host.BridgeLifeAction(0, T0, 0, False, 0, T0 + g) == "cancel"
    assert host.BridgeLifeAction(0, T0, 0, True, T0 - 60_000, T0 + g) == "close"
    # cancel_at platí len pre nevyplnený vstup
    assert host.BridgeLifeAction(T0, 0, 0, False, 0, T0 + g) == "cancel"
    assert host.BridgeLifeAction(T0, 0, 0, True, T0 - 1, T0 + g) == ""
    # hold_ms od fillu
    assert host.BridgeLifeAction(0, 0, 3_600_000, True, T0, T0 + 3_600_000 + g) == "close"
    assert host.BridgeLifeAction(0, 0, 3_600_000, True, T0, T0 + 3_600_000) == ""
    assert host.BridgeLifeAction(0, 0, 3_600_000, False, 0, T0 + 10 ** 9) == ""
    # záložný trailing exekútora: long, aktivácia 10, odstup 5
    assert host.BridgeTrailStop(1, 100.0, 90.0, 108.0, 10.0, 5.0) == pytest.approx(90.0)
    assert host.BridgeTrailStop(1, 100.0, 90.0, 112.0, 10.0, 5.0) == pytest.approx(107.0)
    assert host.BridgeTrailStop(-1, 100.0, 110.0, 88.0, 10.0, 5.0) == pytest.approx(93.0)


def test_life_v_json_zameru(clr):
    core, _ = clr
    w = core.JsonWriter()
    w.BeginObject()
    _entry(core).WriteFields(w)
    w.EndObject()
    assert "life" not in json.loads(w.ToString())
    w = core.JsonWriter()
    w.BeginObject()
    _entry(core, life_close=T0).WriteFields(w)
    w.EndObject()
    assert json.loads(w.ToString())["life"] == {"close_at": T0}


def test_protokol_master_exekutor(clr, tmp_path):
    core, host = clr
    root = str(tmp_path)
    exec_id = host.BridgeExecutorId(5012345, "FTMO Demo")
    assert exec_id == "mt5exec_5012345-FTMO-Demo"

    master = core.BridgeMaster(root, _spec(core, exec_id))
    other = core.BridgeMaster(root, _spec(core, "mt5exec_1-Iny", "ninjatrader_Sim101_MGC_3m_x"))
    assert other.Instance != master.Instance

    h = host.BridgeExecOpen(root, exec_id)
    assert h > 0, host.LastError()
    routes = json.loads(host.BridgeRoutes(h))
    assert [r["id"] for r in routes] == [master.Instance]            # route iného účtu nevidí
    assert routes[0]["symbol"] == "US100.cash" and routes[0]["magic"] == 4711 and routes[0]["qty_mode"] == "value"
    rid = routes[0]["id"]

    c_sync = master.Sync(T0)
    c_entry = master.Entry(T0 + 1, _entry(core, life_close=T0 + 3_600_000), 20000.25, T0 + 360_000)
    c_cancel = master.Cancel(T0 + 2, "L-1", "limitka nevyplnená")
    cmds = json.loads(host.BridgePoll(h, rid))
    assert [c["cid"] for c in cmds] == [c_sync, c_entry, c_cancel]
    assert [c["a"] for c in cmds] == ["sync", "entry", "cancel"]
    e = cmds[1]
    assert e["id"] == "L-1" and e["dir"] == 1 and e["ref"] == 20000.25 and e["exp"] == T0 + 360_000
    assert e["p"]["sl"] == 19980.0 and e["life"] == {"close_at": T0 + 3_600_000}
    assert json.loads(host.BridgePoll(h, rid)) == []                  # druhé čítanie nič nové

    # vybavené sú len sync a entry; cancel exekútor pred „pádom" nestihol
    assert host.BridgeDone(h, rid, c_sync) == 1 and host.BridgeDone(h, rid, c_entry) == 1
    host.BridgeExecClose(h)
    h = host.BridgeExecOpen(root, exec_id)
    again = json.loads(host.BridgePoll(h, rid))
    assert [c["cid"] for c in again] == [c_cancel]                    # nevybavený príde znova, vybavené nie
    assert host.BridgeDone(h, rid, c_cancel) == 1
    host.BridgeExecClose(h)
    h = host.BridgeExecOpen(root, exec_id)
    assert json.loads(host.BridgePoll(h, rid)) == []

    # vybavený príkaz za nevybaveným: po reštarte nevybavený áno, vybavený nie
    c_a = master.Close(T0 + 3, "L-1", "SESSION_END")
    c_b = master.Modify(T0 + 4, "L-1", 19990.0, None, 20010.0, "trailing")
    got = json.loads(host.BridgePoll(h, rid))
    assert [c["cid"] for c in got] == [c_a, c_b] and got[1]["tp"] is None and got[1]["sl"] == 19990.0
    assert host.BridgeDone(h, rid, c_b) == 1
    host.BridgeExecClose(h)
    h = host.BridgeExecOpen(root, exec_id)
    assert [c["cid"] for c in json.loads(host.BridgePoll(h, rid))] == [c_a]

    # udalosti späť; master ich dostane raz, aj nový master (reštart NT) od kurzora
    assert host.BridgeEmit(h, rid, T0 + 10, "fill", c_entry, "L-1", "in", 20150.5, 20000.25, 1.0, 2.0, T0 + 9,
                           "", "") == 1
    assert host.BridgeEmit(h, rid, T0 + 11, "snapshot", c_sync, "", "", 0.0, 0.0, 0.0, 0.0, 0, "", "") == 2
    ev = list(master.Poll())
    assert [str(x["k"]) for x in ev] == ["fill", "snapshot"]
    fill = ev[0]
    assert str(fill["cid"]) == c_entry and float(fill["price_nt"]) == 20000.25 and float(fill["lots"]) == 2.0
    assert "exit" not in fill.Keys
    assert len(list(master.Poll())) == 0
    master2 = core.BridgeMaster(root, _spec(core, exec_id))
    assert master2.Session != master.Session
    assert len(list(master2.Poll())) == 0
    # nový master pokračuje v číslovaní príkazov, cid je unikátne (iná session)
    c_new = master2.Flatten(T0 + 20, "control")
    assert c_new.startswith(master2.Session + "-")
    got = json.loads(host.BridgePoll(h, rid))
    assert got[-1]["cid"] == c_new and got[-1]["seq"] == 6

    # živosť mastera pre exekútor
    assert host.BridgeMasterAge(h, rid, T0) == -1
    master2.Heartbeat(T0 + 100, "enabled")
    assert host.BridgeMasterAge(h, rid, T0 + 1100) == 1000
    assert host.BridgeMasterSession(h, rid) == master2.Session
    host.BridgeExecClose(h)


def _status(master, now):
    from System import String

    detail = String("")
    state, detail = master.Status(now, detail)
    return str(state), str(detail)


def test_stav_route(clr, tmp_path):
    core, host = clr
    root = str(tmp_path)
    exec_id = host.BridgeExecutorId(5012345, "FTMO-Demo")
    master = core.BridgeMaster(root, _spec(core, exec_id))
    rid = master.Instance
    assert _status(master, T0)[0] == "no_executor"

    h = host.BridgeExecOpen(root, exec_id)
    _hb(host, h, T0)
    assert _status(master, T0 + 1000)[0] == "route_pending"           # exekútor route ešte neprevzal
    _hb(host, h, T0, route=(rid, "ok"))
    assert _status(master, T0 + 1000) == ("ok", "")
    assert _status(master, T0 + 3001)[0] == "stale"
    _hb(host, h, T0, margin="netting", route=(rid, "ok"))
    assert _status(master, T0)[0] == "netting_unsupported"
    _hb(host, h, T0, connected=False, route=(rid, "ok"))
    assert _status(master, T0)[0] == "disconnected"
    _hb(host, h, T0, trade=False, route=(rid, "ok"))
    assert _status(master, T0)[0] == "trade_disabled"
    _hb(host, h, T0, symbol="NAS100", route=(rid, "ok"))
    state, detail = _status(master, T0)
    assert state == "symbol_missing" and "US100.cash" in detail
    _hb(host, h, T0, mode=3, route=(rid, "ok"))                       # SYMBOL_TRADE_MODE_CLOSEONLY
    assert _status(master, T0)[0] == "symbol_missing"
    _hb(host, h, T0, route=(rid, "symbol_missing"))                   # stav, ktorý hlási sám exekútor, prejde
    assert _status(master, T0)[0] == "symbol_missing"

    hb = json.loads((tmp_path / "exec" / f"{exec_id}.hb.json").read_text(encoding="utf-8"))
    assert hb["id"] == exec_id and hb["symbols"][0]["name"] == "US100.cash" and hb["routes"] == [{"id": rid, "state": "symbol_missing"}]
    # heartbeat bez symbolov aj route je platný JSON
    assert host.BridgeHbBegin(h, T0, 1, "S", "hedging", True, True, "") == 1 and host.BridgeHbWrite(h) == 1
    hb = json.loads((tmp_path / "exec" / f"{exec_id}.hb.json").read_text(encoding="utf-8"))
    assert hb["symbols"] == [] and hb["routes"] == []
    assert host.BridgeHbWrite(h) == -1 and "HeartbeatBegin" in host.LastError()
    host.BridgeExecClose(h)
    assert host.BridgePoll(h, rid) == "" and str(h) in host.LastError()


def test_druhy_exekutor_s_tym_istym_id_sa_neotvori(clr, tmp_path):
    """EA na druhom grafe (alebo v druhom termináli) by čítalo ten istý cmd.jsonl a každý vstup poslalo dvakrát."""
    _core, host = clr
    root = str(tmp_path)
    exec_id = host.BridgeExecutorId(5012345, "FTMO-Demo")
    h = host.BridgeExecOpen(root, exec_id)
    assert h > 0
    assert host.BridgeExecOpen(root, exec_id) == -1 and "uz bezi" in host.LastError()
    other = host.BridgeExecOpen(root, host.BridgeExecutorId(5012346, "FTMO-Demo"))
    assert other > 0                                                   # iný účet = iný exekútor
    host.BridgeExecClose(h)
    host.BridgeExecClose(h)                                            # druhé zatvorenie nič nerobí
    h2 = host.BridgeExecOpen(root, exec_id)                           # po zatvorení (OnDeinit) znova
    assert h2 > 0
    host.BridgeExecClose(h2)
    host.BridgeExecClose(other)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def test_eod_zatvorenie_podla_hodin(clr):
    core, _ = clr
    tz = core.TimeZones.Get("America/New_York")

    def nxt(local: datetime) -> datetime:
        ms = core.EodCloseEngine.NextClockCloseMs(_ms(local.replace(tzinfo=NY)), tz)
        return datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone(NY).replace(tzinfo=None)

    assert nxt(datetime(2026, 10, 23, 10, 0)) == datetime(2026, 10, 23, 15, 58, 30)     # piatok dopoludnia
    assert nxt(datetime(2026, 10, 23, 15, 58, 30)) == datetime(2026, 10, 26, 15, 58, 30)  # presne v čase -> pondelok
    assert nxt(datetime(2026, 10, 25, 18, 0)) == datetime(2026, 10, 26, 15, 58, 30)     # nedeľa večer (CME open)
    assert nxt(datetime(2026, 10, 26, 18, 30)) == datetime(2026, 10, 27, 15, 58, 30)    # po 18:00 -> ďalší deň
    # cez zmenu letného času v USA (1. 11. 2026): stále 15:58:30 New York
    assert nxt(datetime(2026, 10, 30, 17, 0)) == datetime(2026, 11, 2, 15, 58, 30)


def test_eod_engine_dava_vstupom_life(clr):
    """`noaneteod` na syntetických baroch (ako test_csharp_eod): každý vstup nesie `life.close_at` = najbližších
    15:58:30 NY po zatvorení baru; vstup predlohy bez EOD `life` nemá."""
    from tester.tests.test_csharp_eod import BASES, WRAPS
    from tester.tests.test_csharp_parity import _random_walk, _with_ts
    from tester.tests.test_mt5_static_host import _instrument_json
    from tradebot.core import load_profile
    from tradebot.core.candles import resample_ohlcv
    from tradebot.strategies import get_spec

    core, host = clr
    tz = core.TimeZones.Get("America/New_York")
    profile, tf, loose = BASES["noanet"]
    base = _random_walk(12 * 1440)
    frames = {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 3, 5, 15, 30, 60)}

    def entries(key: str) -> list[tuple[int, dict]]:
        cfg, inst = load_profile(profile, strategy=key)
        for name, value in {**loose, **WRAPS["market"]}.items():
            setattr(cfg, name, value)
        cfg.validate()
        get_spec(key)
        h = host.Create(key, json.dumps(cfg.to_dict()), _instrument_json(inst), tf)
        assert h > 0, host.LastError()
        try:
            htf_min = host.HtfTfMinutes(h)
            htf = list(frames[htf_min].itertuples(index=False)) if htf_min > 0 else []
            j, out = 0, []
            for r in frames[tf].itertuples(index=False):
                while j < len(htf) and int(htf[j].ts) + htf_min * 60_000 <= int(r.ts):
                    b = htf[j]
                    host.FeedHtf(h, int(b.ts), float(b.open), float(b.high), float(b.low), float(b.close), float(b.volume))
                    j += 1
                raw = host.OnBar(h, int(r.ts), float(r.open), float(r.high), float(r.low), float(r.close),
                                 float(r.volume), 0.0, False, "")
                assert raw, host.LastError()
                out += [(int(r.ts), o) for o in json.loads(raw).get("o", []) if o["a"] == "entry"]
            return out
        finally:
            host.Destroy(h)

    eod = entries("noaneteod")
    assert len(eod) > 5
    for bt, o in eod:
        assert o["life"] == {"close_at": core.EodCloseEngine.NextClockCloseMs(bt + tf * 60_000, tz)}, (bt, o)
    assert all("life" not in o for _, o in entries("noanet"))


def test_rucny_master_cli(clr, tmp_path, capsys):
    """`python -m tradebot.live.bridge` píše tie isté príkazy ako NinjaTrader — exekútor ich prečíta cez fasádu."""
    from tradebot.live import bridge as cli

    _, host = clr
    root = str(tmp_path)
    to = host.BridgeExecutorId(5012345, "FTMO-Demo")
    base = ["--root", root, "--to", to, "--symbol", "US100.cash"]
    assert cli.main(["status", *base]) == 1 and "no_executor" in capsys.readouterr().out
    assert cli.main(["send", "entry", *base, "--id", "M-1", "--e", "20000", "--sl", "19980", "--tp", "20040",
                     "--ref", "20010", "--close-in", "30"]) == 0
    assert cli.main(["send", "modify", *base, "--id", "M-1", "--sl", "19990", "--ref", "20010"]) == 0
    assert cli.main(["send", "sync", *base]) == 0
    h = host.BridgeExecOpen(root, to)
    cmds = json.loads(host.BridgePoll(h, "manual_US100.cash"))
    assert [c["a"] for c in cmds] == ["entry", "modify", "sync"]
    assert cmds[0]["ot"] == "Limit" and cmds[0]["ref"] == 20010.0 and cmds[0]["life"]["close_at"] > cmds[0]["t"]
    assert cmds[1]["sl"] == 19990.0 and cmds[1]["tp"] is None
    assert host.BridgeMasterAge(h, "manual_US100.cash", T0 * 2) >= 0
    host.BridgeExecClose(h)
    assert cli.main(["execs", "--root", root]) == 1
