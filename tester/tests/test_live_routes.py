"""Smerovanie orderov nasadenia NinjaTradera do MT5 exekútora na hube a u agenta (docs/ROUTING.md, fáza 4).

* `tradebot.live.routes`: symbol u brokera z tabuľky, aliasu MT5 účtu alebo nasadenia; kontrola route;
  id exekútora rovnaké ako `Bridge.ExecutorId` v C#;
* `DeployStore`: route je súčasť nasadenia (PATCH ju nemení), aliasy pri účte, MT5 účet s route sa nezmaže,
  `desired_for_agent` doplní `route.to` a virtuálne nasadenie exekútora (jeden na MT5 účet a stroj);
* drivery: NinjaTrader zapíše `route` do deploy.json, MT5 dá exekútorovi graf `TradeBotExecutor` bez profilu
  a bez control súboru.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tester.tests.test_live_deploy import Clock, _resolver
from tester.tests.test_live_drivers_mt5 import drv  # noqa: F401 (fixture)
from tradebot.live.deploy import EXECUTOR_PREFIX, Conflict, DeployError, DeployStore
from tradebot.live.drivers.base import Account, Deployment
from tradebot.live.drivers.ninjatrader import NinjaTraderDriver
from tradebot.live.routes import RouteError, cfd_symbol, executor_id, normalize_route
from tradebot.live.vault import Vault

MT5 = {"id": "ftmo", "platform": "mt5", "login": "1514750898", "server": "FTMO-Demo", "symbols": {"NAS100": "US100.cash"}}


def test_symbol_a_kontrola_route():
    assert cfd_symbol("MNQ 12-26") == ("NAS100", 1.0)
    assert cfd_symbol("MNQ 12-26", {"NAS100": "US100.cash"}) == ("US100.cash", 1.0)
    assert cfd_symbol("MGC 02-27", {"NAS100": "US100.cash"}) == ("XAUUSD", 1.0)
    assert cfd_symbol("ZB 12-26") == (None, 1.0)
    assert cfd_symbol("ZB 12-26", {"ZB": "USTBOND"}) == ("USTBOND", 1.0)   # alias aj na koreň futures
    assert executor_id(1514750898, "FTMO Demo") == "mt5exec_1514750898-FTMO-Demo"

    r = normalize_route({"via": "mt5", "account": "ftmo"}, nt_symbol="MNQ 12-26", nt_platform="ninjatrader", mt5_account=MT5)
    assert r == {"via": "mt5", "account": "ftmo", "symbol": "US100.cash", "price": "basis", "scale": 1.0,
                 "qty": {"mode": "value"}}
    r = normalize_route({"account": "ftmo", "symbol": "USTEC", "qty": {"mode": "fixed", "lots": 0.5}, "price": "same"},
                        nt_symbol="MNQ 12-26", nt_platform="ninjatrader", mt5_account=MT5)
    assert r["symbol"] == "USTEC" and r["qty"] == {"mode": "fixed", "lots": 0.5} and r["price"] == "same"
    assert normalize_route(None, nt_symbol="MNQ", nt_platform="ninjatrader", mt5_account=None) is None

    zle = [({"account": "ftmo"}, "mt5", MT5, "len nasadenie NinjaTradera"),
           ({}, "ninjatrader", MT5, None),
           ({"via": "ib", "account": "ftmo"}, "ninjatrader", MT5, "len mt5"),
           ({"account": ""}, "ninjatrader", MT5, "MT5 účet"),
           ({"account": "x"}, "ninjatrader", None, "neexistuje"),
           ({"account": "sim"}, "ninjatrader", {"id": "sim", "platform": "ninjatrader"}, "nie je MetaTrader 5"),
           ({"account": "ftmo", "qty": {"mode": "fixed"}}, "ninjatrader", MT5, "lots"),
           ({"account": "ftmo", "price": "mid"}, "ninjatrader", MT5, "price"),
           ({"account": "ftmo", "scale": 0}, "ninjatrader", MT5, "kladné")]
    for route, platform, acc, text in zle:
        if text is None:
            assert normalize_route(route, nt_symbol="MNQ 12-26", nt_platform=platform, mt5_account=acc) is None
            continue
        with pytest.raises(RouteError, match=text):
            normalize_route(route, nt_symbol="MNQ 12-26", nt_platform=platform, mt5_account=acc)
    with pytest.raises(RouteError, match="nepoznám symbol"):
        normalize_route({"account": "ftmo"}, nt_symbol="ZB 12-26", nt_platform="ninjatrader", mt5_account=MT5)


@pytest.fixture
def store(tmp_path: Path):
    return DeployStore(tmp_path / "live.sqlite", clock=Clock(), config_resolver=_resolver, vault=Vault(key=b"k" * 32),
                       strategy_check=lambda k: k)


def _ucty(store: DeployStore):
    store.upsert_account({"platform": "mt5", "label": "ftmo", "login": "1514750898", "server": "FTMO-Demo",
                          "symbols": {"NAS100": "US100.cash"}}, by="rasto", password="tajne")
    store.upsert_account({"platform": "ninjatrader", "label": "sim", "login": "Sim101", "server": "Rithmic"}, by="rasto")


def test_route_v_nasadeni_a_exekutor_v_pozadovanom_stave(store: DeployStore):
    _ucty(store)
    assert store.account("ftmo")["symbols"] == {"NAS100": "US100.cash"}
    rev = store.account("ftmo")["rev"]
    store.upsert_account({"id": "ftmo", "symbols": {"NAS100": "US100.cash", "XAUUSD": "XAUUSD.r"}}, by="rasto")
    assert store.account("ftmo")["symbols"]["XAUUSD"] == "XAUUSD.r" and store.account("ftmo")["rev"] == rev   # nie nové prihlásenie

    a = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "ibsnet", "symbol": "MNQ 12-26",
                                 "tf": 3, "profile": "p1", "route": {"via": "mt5", "account": "ftmo"}}, by="rasto")
    assert a["route"] == {"via": "mt5", "account": "ftmo", "symbol": "US100.cash", "price": "basis", "scale": 1.0,
                          "qty": {"mode": "value"}}
    b = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "orbnet", "symbol": "MGC 02-27",
                                 "tf": 5, "profile": "p1", "route": {"account": "ftmo"}}, by="rasto")
    c = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "noanet", "symbol": "MNQ 12-26",
                                 "tf": 5, "profile": "p1"}, by="rasto")
    assert b["route"]["symbol"] == "XAUUSD.r" and c["route"] is None
    with pytest.raises(DeployError, match="nemení"):
        store.update_deployment(a["id"], {"route": {"account": "ftmo", "symbol": "USTEC"}}, by="rasto")
    with pytest.raises(DeployError, match="len nasadenie NinjaTradera"):
        store.create_deployment({"account": "ftmo", "agent": "trade-pc", "strategy": "ibsnet", "symbol": "US100.cash",
                                 "tf": 3, "profile": "p1", "route": {"account": "ftmo"}}, by="rasto")
    with pytest.raises(DeployError, match="neexistuje"):
        store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "tksnet", "symbol": "MNQ 12-26",
                                 "tf": 3, "profile": "p1", "route": {"account": "nie"}}, by="rasto")

    want = store.desired_for_agent("trade-pc")
    deps = {d["id"]: d for d in want["deployments"]}
    to = "mt5exec_1514750898-FTMO-Demo"
    assert deps[a["id"]]["route"]["to"] == to and deps[b["id"]]["route"]["to"] == to and deps[c["id"]]["route"] is None
    ex = deps[EXECUTOR_PREFIX + "ftmo"]
    assert ex["kind"] == "executor" and ex["account"] == "ftmo" and ex["active"] is True and ex["instance"] == to
    assert ex["symbol"] == "US100.cash" and ex["tf"] == 1 and ex["terminal"] == "" and ex["portable"] is False
    accs = {x["id"]: x for x in want["accounts"]}
    assert set(accs) == {"ftmo", "sim"} and accs["ftmo"]["secret"] == "tajne"   # MT5 účet aj s heslom na tento stroj
    assert len([d for d in want["deployments"] if d.get("kind") == "executor"]) == 1
    assert store.desired_for_agent("iny-pc")["deployments"] == []

    # MT5 účet, na ktorý smerujú ordery, sa nezmaže (ani pri neaktívnych nasadeniach - po reaktivácii by bez
    # exekútora obchodovali na účte NinjaTradera, audit H1); po odstránení nasadení exekútor neaktívny
    with pytest.raises(Conflict, match="smerujú ordery"):
        store.delete_account("ftmo", by="rasto")
    store.delete_deployment(a["id"], by="rasto")
    store.delete_deployment(b["id"], by="rasto")
    with pytest.raises(Conflict, match="neaktívne"):
        store.delete_account("ftmo", by="rasto")
    ex = {d["id"]: d for d in store.desired_for_agent("trade-pc")["deployments"]}[EXECUTOR_PREFIX + "ftmo"]
    assert ex["active"] is False
    # reaktivácia bez MT5 účtu v hube sa odmietne
    store._db.execute("DELETE FROM accounts WHERE id = 'ftmo'")
    with pytest.raises(Conflict, match="bez exekútora"):
        store.update_deployment(a["id"], {"active": True}, by="rasto")
    store.upsert_account({"id": "ftmo", "platform": "mt5", "login": "1514750898", "server": "FTMO-Demo"}, by="rasto")
    assert store.update_deployment(a["id"], {"active": True}, by="rasto")["active"] is True
    store.delete_deployment(a["id"], by="rasto")
    store.delete_deployment(a["id"], by="rasto", force=True)
    store.delete_deployment(b["id"], by="rasto", force=True)
    assert EXECUTOR_PREFIX + "ftmo" not in {d["id"] for d in store.desired_for_agent("trade-pc")["deployments"]}
    assert store.delete_account("ftmo", by="rasto")["deleted"] is True


def test_ninjatrader_driver_zapise_route(tmp_path: Path, monkeypatch):
    nt = tmp_path / "NinjaTrader 8"
    (nt / "bin" / "Custom").mkdir(parents=True)
    monkeypatch.setenv("TRADEBOT_NT_DIR", str(nt))
    d = NinjaTraderDriver(exe=tmp_path / "NinjaTrader.exe", is_running=lambda: True, launcher=lambda p: None)
    acc = Account.from_dict({"id": "sim", "platform": "ninjatrader", "login": "Sim101", "server": "Rithmic"})
    route = {"via": "mt5", "account": "ftmo", "symbol": "US100.cash", "price": "basis", "scale": 1.0,
             "qty": {"mode": "value"}, "to": "mt5exec_1514750898-FTMO-Demo"}
    a = Deployment.from_dict({"id": "n1", "account": "sim", "strategy": "ibsnet", "symbol": "MNQ 12-26", "tf": 3,
                              "profile": "p1", "route": route})
    b = Deployment.from_dict({"id": "n2", "account": "sim", "strategy": "orbnet", "symbol": "MNQ 12-26", "tf": 5,
                              "profile": "p1"})   # bez route = lokálne
    d.ensure_instance(acc, [a, b])
    inst = {e["deployment"]: e for e in json.loads((nt / "TradeBot" / "deploy.json").read_text(encoding="utf-8"))["instances"]}
    assert inst["n1"]["route"] == {"via": "mt5", "to": "mt5exec_1514750898-FTMO-Demo", "symbol": "US100.cash",
                                   "price": "basis", "scale": 1.0, "qty": {"mode": "value"}, "magic": 0}
    assert "route" not in inst["n2"]
    # route bez `to` (MT5 účet z hubu zmizol) sa NESMIE potichu zapísať ako lokálne obchodovanie (audit H1):
    # reconciler ju odmietne pri validácii nasadenia
    c = Deployment.from_dict({"id": "n3", "account": "sim", "strategy": "orbnet", "symbol": "MNQ 12-26", "tf": 5,
                              "profile": "p1", "route": {**route, "to": ""}})
    assert c.route is None
    with pytest.raises(ValueError, match="nemá exekútora"):
        c.validate()


def test_mt5_driver_da_exekutorovi_graf_bez_profilu(drv):  # noqa: F811
    d, procs, clock, data, common = drv
    acc = Account.from_dict({"id": "ftmo", "platform": "mt5", "login": "1514750898", "server": "FTMO-Demo"})
    ex = Deployment.from_dict({"id": EXECUTOR_PREFIX + "ftmo", "account": "ftmo", "kind": "executor", "strategy": "executor",
                               "symbol": "US100.cash", "tf": 1, "profile": "executor", "mode": "enabled", "active": True,
                               "instance": "mt5exec_1514750898-FTMO-Demo"})
    assert ex.is_executor and ex.route is None
    ex.validate()
    d.ensure_profile(ex)
    d.write_control(ex)
    assert not (common / "TradeBot" / "profiles" / "executor").exists()
    assert not (common / "TradeBot" / "control").exists() or not list((common / "TradeBot" / "control").glob("*.json"))
    charts = d._charts(acc, [ex])
    assert charts[0]["expert"] == "TradeBotExecutor" and charts[0]["path"] == "Experts\\TradeBot\\TradeBotExecutor.ex5"
    assert charts[0]["inputs"] == {} and charts[0]["symbol"] == "US100.cash" and charts[0]["tf"] == 1
