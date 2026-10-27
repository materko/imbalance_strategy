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
import re
from pathlib import Path

import pytest

from tester.tests.test_live_deploy import Clock, _resolver
from tester.tests.test_live_drivers_mt5 import drv  # noqa: F401 (fixture)
from tradebot.live.deploy import EXECUTOR_PREFIX, Conflict, DeployError, DeployStore
from tradebot.live.drivers.base import Account, Deployment
from tradebot.live.drivers.ninjatrader import NinjaTraderDriver
from tradebot.live.routes import PRICE_MODES, QTY_MODES, RouteError, cfd_symbol, executor_id, normalize_route
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


def test_exekutor_graf_hlasenie_a_platforma_uctu(store: DeployStore):
    """H5: graf exekútora na symbole najstaršej route; H6: chyba exekútora pri nasadení; H4: platforma sa nemení."""
    _ucty(store)
    b = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "orbnet", "symbol": "MGC 02-27",
                                 "tf": 5, "profile": "p1", "route": {"account": "ftmo"}}, by="rasto")
    a = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "ibsnet", "symbol": "MNQ 12-26",
                                 "tf": 3, "profile": "p1", "route": {"account": "ftmo"}}, by="rasto")
    ex = {d["id"]: d for d in store.desired_for_agent("trade-pc")["deployments"]}[EXECUTOR_PREFIX + "ftmo"]
    assert ex["symbol"] == "XAUUSD"              # najstaršia route, nie abecedne prvý US100.cash

    # hlásenie agenta k exekútoru sa ukáže pri nasadeniach, ktoré naň smerujú; cudzí stroj ho nezapíše
    rep = [{"deployment": EXECUTOR_PREFIX + "ftmo", "status": "error", "error": "driver pre platformu 'mt5' nie je na tomto stroji"}]
    assert store.report_applied("iny-pc", rep) == 0
    assert store.report_applied("trade-pc", rep) == 1
    deps = {d["id"]: d for d in store.deployments()}
    assert deps[a["id"]]["executor"]["status"] == "error" and "mt5" in deps[a["id"]]["executor"]["error"]
    assert store.deployment(b["id"])["executor"]["error"] == deps[a["id"]]["executor"]["error"]

    with pytest.raises(Conflict, match="smerujú ordery"):
        store.upsert_account({"id": "ftmo", "platform": "ninjatrader"}, by="rasto")
    assert store.account("ftmo")["platform"] == "mt5"

    for d in (a, b):
        store.delete_deployment(d["id"], by="rasto")
        store.delete_deployment(d["id"], by="rasto", force=True)
    store.delete_account("ftmo", by="rasto")
    assert store._db.execute("SELECT COUNT(*) FROM applied WHERE deployment LIKE 'exec-%'").fetchone()[0] == 0


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


# --------------------------------------------------------------------------- #
# nízke nálezy auditu smerovania (docs/audity/AUDIT_routing_2026-10-26.md, časť 4)


def test_alias_na_koren_futures_vyhra_nad_tabulkou():
    aliasy = {"MNQ": "USTEC", "NAS100": "US100.cash"}
    assert cfd_symbol("MNQ 12-26", aliasy) == ("USTEC", 1.0)
    assert cfd_symbol("NQ 12-26", aliasy) == ("US100.cash", 1.0)       # iný koreň ide cez alias CFD
    r = normalize_route({"account": "ftmo"}, nt_symbol="MNQ 12-26", nt_platform="ninjatrader",
                        mt5_account={**MT5, "symbols": aliasy})
    assert r["symbol"] == "USTEC"


@pytest.mark.parametrize("route", [{"scale": float("nan")}, {"scale": float("inf")}, {"scale": "inf"},
                                   {"scale": "-inf"}, {"qty": {"mode": "fixed", "lots": float("nan")}},
                                   {"qty": {"mode": "fixed", "lots": "inf"}}])
def test_nan_a_inf_v_route_neprejdu(route):
    with pytest.raises(RouteError, match="konečné"):
        normalize_route({"account": "ftmo", **route}, nt_symbol="MNQ 12-26", nt_platform="ninjatrader", mt5_account=MT5)


def test_zle_aliasy_existujuceho_uctu_su_chyba_vstupu(store: DeployStore):
    _ucty(store)
    with pytest.raises(DeployError, match="symbols účtu") as exc:
        store.upsert_account({"id": "ftmo", "symbols": "NAS100=US100.cash"}, by="rasto")
    assert not isinstance(exc.value, RouteError)
    assert store.account("ftmo")["symbols"] == {"NAS100": "US100.cash"}


def test_poskodena_route_nezhodi_pozadovany_stav_a_nie_je_lokalna(store: DeployStore):
    _ucty(store)
    a = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "ibsnet", "symbol": "MNQ 12-26",
                                 "tf": 3, "profile": "p1", "route": {"account": "ftmo"}}, by="rasto")
    b = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "orbnet", "symbol": "MGC 02-27",
                                 "tf": 5, "profile": "p1", "route": {"account": "ftmo"}}, by="rasto")
    store._db.execute("UPDATE deployments SET route = '{\"account\": \"ftmo\", ' WHERE id = ?", (a["id"],))
    store._db.commit()
    deps = {d["id"]: d for d in store.desired_for_agent("trade-pc")["deployments"]}
    assert "poškodená" in deps[a["id"]]["route"]["error"] and "to" not in deps[a["id"]]["route"]
    assert deps[b["id"]]["route"]["to"] == "mt5exec_1514750898-FTMO-Demo"     # ostatné nasadenia idú ďalej
    assert deps[EXECUTOR_PREFIX + "ftmo"]["active"] is True
    dep = Deployment.from_dict(deps[a["id"]])
    assert dep.route is None
    with pytest.raises(ValueError, match="poškodená"):
        dep.validate()                                   # agent ju nezapíše — nikdy nie ako lokálne obchodovanie
    assert {d["id"] for d in store.deployments()} >= {a["id"], b["id"]}
    store.delete_deployment(a["id"], by="rasto")
    with pytest.raises(Conflict, match="poškodená"):
        store.update_deployment(a["id"], {"active": True}, by="rasto")


def test_executor_id_cisla_a_server():
    assert executor_id("007", "FTMO-Demo") == "mt5exec_7-FTMO-Demo"     # C# berie login ako long
    assert executor_id(" 1514750898 ", "FTMO Demo") == "mt5exec_1514750898-FTMO-Demo"
    assert executor_id(5, "ftmo-demo") == "mt5exec_5-ftmo-demo"          # veľkosť písmen servera ostáva
    assert executor_id(5, None) == "mt5exec_5-"
    assert executor_id(5, "Šrv/1") == "mt5exec_5--rv-1"


def _hb_exekutora(root: Path, exec_id: str, t_ms: int, symbols: list[str]) -> None:
    (root / "exec").mkdir(parents=True, exist_ok=True)
    (root / "exec" / f"{exec_id}.hb.json").write_text(json.dumps(
        {"t": t_ms, "id": exec_id, "symbols": [{"name": s, "tick": 0.01} for s in symbols], "routes": []}), encoding="utf-8")


def test_agent_hlasi_symboly_exekutora(tmp_path: Path, monkeypatch):
    from tester.tests.test_live_apply import FakeDriver, dep, desired
    from tradebot.live.apply import Reconciler

    monkeypatch.setenv("TRADEBOT_BRIDGE_ROOT", str(tmp_path / "bridge"))
    now = 1_790_000_000.0
    to = "mt5exec_1514750898-FTMO-Demo"
    acc = {"id": "ftmo", "platform": "mt5", "label": "FTMO", "login": "1514750898", "server": "FTMO-Demo",
           "terminal": "", "portable": False}
    rec = Reconciler({"mt5": FakeDriver()}, tmp_path / "s.json", clock=lambda: now)
    ex = dep("exec-ftmo", kind="executor", strategy="executor", profile="executor", config={}, config_hash="",
             symbol="US100.cash", mode="enabled", instance=to)
    rec.run(desired(ex, accounts=(acc,)))
    assert rec.fragment()["exec_symbols"] == {}                           # exekútor ešte nič nenapísal
    _hb_exekutora(tmp_path / "bridge", to, int((now - 5) * 1000), ["US100.cash", "XAUUSD", "US100.cash"])
    assert rec.fragment()["exec_symbols"] == {"ftmo": ["US100.cash", "XAUUSD"]}
    _hb_exekutora(tmp_path / "bridge", to, int((now - 3600) * 1000), ["US100.cash"])
    assert rec.fragment()["exec_symbols"] == {}                           # starý heartbeat sa nehlási


def test_hub_odmietne_symbol_ktory_ucet_nema(store: DeployStore):
    _ucty(store)
    a = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "ibsnet", "symbol": "MNQ 12-26",
                                 "tf": 3, "profile": "p1", "route": {"account": "ftmo", "symbol": "USTEC"}}, by="rasto")
    assert store.account("ftmo")["exec_symbols"] is None                 # nikto nehlásil = bez kontroly
    # cudzí stroj (nič z neho na účet nesmeruje) ani NT účet zoznam nezapíšu
    store.report_applied("iny-pc", [], exec_symbols={"ftmo": ["X"]})
    store.report_applied("trade-pc", [], exec_symbols={"sim": ["X"]})
    assert store.account("ftmo")["exec_symbols"] is None and store.account("sim")["exec_symbols"] is None
    store.report_applied("trade-pc", [], exec_symbols={"ftmo": ["US100.cash", "XAUUSD.r"]})
    assert store.account("ftmo")["exec_symbols"] == ["US100.cash", "XAUUSD.r"]
    store.report_applied("trade-pc", [], exec_symbols={"ftmo": []})       # prázdny Market Watch neprepíše známy
    assert store.account("ftmo")["exec_symbols"] == ["US100.cash", "XAUUSD.r"]
    with pytest.raises(DeployError, match="nemá symbol 'USTEC'"):
        store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "orbnet", "symbol": "MNQ 12-26",
                                 "tf": 5, "profile": "p1", "route": {"account": "ftmo", "symbol": "USTEC"}}, by="rasto")
    with pytest.raises(DeployError, match="myslel si US100.cash"):
        store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "orbnet", "symbol": "MNQ 12-26",
                                 "tf": 5, "profile": "p1", "route": {"account": "ftmo", "symbol": "us100.CASH"}}, by="rasto")
    ok = store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "orbnet", "symbol": "MNQ 12-26",
                                  "tf": 5, "profile": "p1", "route": {"account": "ftmo"}}, by="rasto")
    assert ok["route"]["symbol"] == "US100.cash" and a["route"]["symbol"] == "USTEC"


def test_hub_heartbeat_ulozi_symboly_exekutora(store: DeployStore, tmp_path: Path):
    from tester.hub.state import HubState

    _ucty(store)
    store.create_deployment({"account": "sim", "agent": "trade-pc", "strategy": "ibsnet", "symbol": "MNQ 12-26",
                             "tf": 3, "profile": "p1", "route": {"account": "ftmo"}}, by="rasto")
    state = HubState(tmp_path / "hub", token="hlavny")
    state.deploy = store
    state._live_report("trade-pc", {}, {"applied": [], "exec_symbols": {"ftmo": ["US100.cash"]}})
    assert store.account("ftmo")["exec_symbols"] == ["US100.cash"]
    state._live_report("trade-pc", {}, {"applied": [], "exec_symbols": "zle"})   # zlý tvar nič nezhodí
    assert store.account("ftmo")["exec_symbols"] == ["US100.cash"]


def test_migracia_starej_databazy_uctov(tmp_path: Path):
    import sqlite3

    path = tmp_path / "old.sqlite"
    db = sqlite3.connect(str(path))
    db.executescript("""
        CREATE TABLE accounts (id TEXT PRIMARY KEY, agent TEXT NOT NULL, platform TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '', login TEXT NOT NULL DEFAULT '', server TEXT NOT NULL DEFAULT '',
            terminal TEXT NOT NULL DEFAULT '', portable INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL,
            updated REAL NOT NULL, by TEXT NOT NULL DEFAULT '', secret_pending TEXT);
        INSERT INTO accounts (id, agent, platform, login, server, created, updated) VALUES ('ftmo', '', 'mt5', '1', 'S', 0, 0);
    """)
    db.commit()
    db.close()
    s = DeployStore(path, clock=Clock(), config_resolver=_resolver, vault=Vault(key=b"k" * 32), strategy_check=lambda k: k)
    acc = s.account("ftmo")
    assert acc["symbols"] == {} and acc["exec_symbols"] is None
    s.close()


def test_rezimy_route_vo_formulari_a_v_jadre():
    """Režimy route sú v Pythone, C# jadre a formulári webapp zvlášť (audit, duplicity) — musia sa zhodovať."""
    repo = Path(__file__).resolve().parents[2]
    html = (repo / "tester" / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    sel = re.search(r'<select id="ld-d-route-qty">(.*?)</select>', html, re.S)
    assert sel and tuple(re.findall(r'<option value="([^"]+)"', sel.group(1))) == QTY_MODES
    cs = (repo / "tradebot" / "core" / "ports" / "csharp" / "TradeBot.Core" / "Bridge.cs").read_text(encoding="utf-8")
    assert f'public string Price = "{PRICE_MODES[0]}";' in cs and f'public string QtyMode = "{QTY_MODES[0]}";' in cs
    assert f'mode == "{QTY_MODES[1]}"' in cs
    mqh = (repo / "tradebot" / "adapters" / "mt5" / "TradeBotExecutor.mqh").read_text(encoding="utf-8")
    assert f'.price == "{PRICE_MODES[1]}"' in mqh and f'.qtyMode == "{QTY_MODES[1]}"' in mqh
