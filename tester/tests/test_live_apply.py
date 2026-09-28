"""`tradebot.live.apply.Reconciler` s falošným driverom (docs/LIVE.md, fáza 2b): poradie volaní,
idempotencia (druhé kolo bez zmeny nič nepíše), izolácia chýb po nasadeniach, ack hesla, stav na
disku prežije nový reconciler, nasadenie zmiznuté z hubu sa odstráni; a agent hubu: `live` v tele
heartbeatu (inštancie zo spoolu + `applied`) a `live` z odpovede → reconciler v pomalom kroku."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.live.apply import Reconciler, config_hash
from tradebot.live.drivers.base import Account, Deployment, Driver
from tradebot.live.schema import instance_id


class FakeDriver(Driver):
    platform = "mt5"

    def __init__(self, fail: dict[str, str] | None = None) -> None:
        self.calls: list[tuple] = []
        self.fail = fail or {}      # názov metódy → id nasadenia/účtu, pri ktorom má padnúť
        self.secrets: dict[str, str] = {}
        self.removed: list[str] = []    # id inštancií, ktoré prešli `remove_instance`

    def available(self) -> bool:
        return True

    def spool_account(self, account: Account) -> str:
        return f"{account.login}-{account.server}"

    def _maybe_fail(self, method: str, ident: str) -> None:
        if self.fail.get(method) == ident:
            raise RuntimeError(f"{method} zlyhalo pre {ident}")

    def store_secret(self, account, password):
        self._maybe_fail("store_secret", account.id)
        self.calls.append(("store_secret", account.id))
        self.secrets[account.id] = password

    def ensure_profile(self, deployment):
        self._maybe_fail("ensure_profile", deployment.id)
        self.calls.append(("ensure_profile", deployment.id, deployment.profile))
        return Path(f"/p/{deployment.profile}.json")

    def write_control(self, deployment):
        self._maybe_fail("write_control", deployment.id)
        self.calls.append(("write_control", deployment.id, deployment.instance, deployment.mode))
        return Path(f"/c/{deployment.instance}.json")

    def ensure_instance(self, account, deployments):
        self._maybe_fail("ensure_instance", account.id)
        self.calls.append(("ensure_instance", account.id, tuple(d.id for d in deployments)))

    def remove_instance(self, account, deployment):
        self._maybe_fail("remove_instance", deployment.id)
        self.calls.append(("remove_instance", account.id, deployment.id))
        self.removed.append(deployment.instance)

    def status(self, account):
        return {"running": True, "account": account.id}


ACC = {"id": "ftmo", "platform": "mt5", "label": "FTMO demo", "login": "1514750898", "server": "FTMO-Demo",
       "terminal": "", "portable": False}
CFG = {"_strategy": "ibsnet", "rrRatio": 3.0}


def dep(i: str, **over) -> dict:
    d = {"id": i, "account": "ftmo", "strategy": "ibsnet", "symbol": "US100.cash", "tf": 1,
         "profile": "golden_binance_btcusdt_3m", "config": CFG, "config_hash": config_hash(CFG),
         "mode": "paused", "active": True}
    d.update(over)
    return d


def desired(*deps, accounts=(ACC,)) -> dict:
    return {"accounts": [dict(a) for a in accounts], "deployments": list(deps)}


def kinds(calls, name):
    return [c for c in calls if c[0] == name]


def test_run_order_idempotency_and_applied(tmp_path: Path):
    drv = FakeDriver()
    rec = Reconciler({"mt5": drv}, tmp_path / "apply_state.json")
    d1, d2 = dep("d1"), dep("d2", symbol="EURUSD", tf=5, profile="multicharts_mnq_3m", mode="enabled")
    out = rec.run(desired(d1, d2))

    inst1 = instance_id("mt5", "1514750898-FTMO-Demo", "US100.cash", 1, "ibsnet")
    assert drv.calls == [
        ("ensure_profile", "d1", "golden_binance_btcusdt_3m"), ("write_control", "d1", inst1, "paused"),
        ("ensure_profile", "d2", "multicharts_mnq_3m"),
        ("write_control", "d2", instance_id("mt5", "1514750898-FTMO-Demo", "EURUSD", 5, "ibsnet"), "enabled"),
        ("ensure_instance", "ftmo", ("d1", "d2")),
    ]
    assert out["secret_ack"] == []
    applied = {a["deployment"]: a for a in out["applied"]}
    assert applied["d1"] == {"deployment": "d1", "config_hash": config_hash(CFG), "mode": "paused", "active": True,
                             "status": "ok", "error": ""}
    assert applied["d2"]["status"] == "ok" and "sig" not in applied["d2"]

    # druhé kolo bez zmeny: žiadny zápis profilu ani control, len kontrola inštancie (spadnutý terminál)
    drv.calls.clear()
    rec.run(desired(d1, d2))
    assert drv.calls == [("ensure_instance", "ftmo", ("d1", "d2"))]
    assert all(a["status"] == "ok" for a in rec.fragment()["applied"])

    # zmena režimu jedného: len jeho control (a profil) sa píše znova
    drv.calls.clear()
    rec.run(desired(dep("d1", mode="enabled"), d2))
    assert drv.calls == [("ensure_profile", "d1", "golden_binance_btcusdt_3m"), ("write_control", "d1", inst1, "enabled"),
                         ("ensure_instance", "ftmo", ("d1", "d2"))]

    # zmena configu pri rovnakom profile: tiež
    drv.calls.clear()
    novy = {**CFG, "rrRatio": 4.0}
    rec.run(desired(dep("d1", mode="enabled", config=novy, config_hash=config_hash(novy)), d2))
    assert kinds(drv.calls, "ensure_profile") == [("ensure_profile", "d1", "golden_binance_btcusdt_3m")]
    assert {a["deployment"]: a["config_hash"] for a in rec.fragment()["applied"]}["d1"] == config_hash(novy)


def test_error_isolation_per_deployment_and_account(tmp_path: Path):
    drv = FakeDriver(fail={"ensure_profile": "d2"})
    rec = Reconciler({"mt5": drv}, tmp_path / "s.json")
    out = rec.run(desired(dep("d1"), dep("d2", symbol="EURUSD")))
    applied = {a["deployment"]: a for a in out["applied"]}
    assert applied["d1"]["status"] == "ok"
    assert applied["d2"]["status"] == "error" and "ensure_profile zlyhalo pre d2" in applied["d2"]["error"]
    # zlyhané nasadenie sa do inštancie nedostane, ostatné áno
    assert kinds(drv.calls, "ensure_instance") == [("ensure_instance", "ftmo", ("d1",))]

    # ďalšie kolo: chybné sa skúša znova, dobré sa nepíše
    drv.fail.clear()
    drv.calls.clear()
    rec.run(desired(dep("d1"), dep("d2", symbol="EURUSD")))
    assert [c[:2] for c in drv.calls] == [("ensure_profile", "d2"), ("write_control", "d2"), ("ensure_instance", "ftmo")]
    assert all(a["status"] == "ok" for a in rec.fragment()["applied"])

    # chyba inštancie účtu = error ku všetkým jeho aktívnym nasadeniam, iný účet nedotknutý
    drv2 = FakeDriver(fail={"ensure_instance": "ftmo"})
    rec2 = Reconciler({"mt5": drv2}, tmp_path / "s2.json")
    acc_b = {**ACC, "id": "druhy", "login": "7"}
    out = rec2.run(desired(dep("d1"), dep("d3", account="druhy"), accounts=(ACC, acc_b)))
    applied = {a["deployment"]: a for a in out["applied"]}
    assert applied["d1"]["status"] == "error" and applied["d1"]["error"].startswith("inštancia:")
    assert applied["d3"]["status"] == "ok"

    # neznáma platforma / chýbajúci účet / neplatné nasadenie = error, nie pád
    rec3 = Reconciler({"mt5": FakeDriver()}, tmp_path / "s3.json")
    out = rec3.run(desired(dep("d1", account="nikto"), dep("d4", symbol=""), dep("d5", account="nt"),
                           accounts=(ACC, {**ACC, "id": "nt", "platform": "ninjatrader"})))
    applied = {a["deployment"]: a for a in out["applied"]}
    assert "nie je v zozname účtov" in applied["d1"]["error"]
    assert "symbol" in applied["d4"]["error"]
    assert "driver pre platformu 'ninjatrader'" in applied["d5"]["error"]
    assert rec3.status()["accounts"]["nt"]["error"].startswith("driver pre platformu")

    # výnimka drivera mimo nasadení (status) nezhodí status reconcilera
    assert rec3.status()["accounts"]["ftmo"]["driver"] == {"running": True, "account": "ftmo"}


def test_secret_is_stored_acked_and_never_persisted(tmp_path: Path):
    drv = FakeDriver()
    state = tmp_path / "s.json"
    rec = Reconciler({"mt5": drv}, state)
    out = rec.run(desired(dep("d1"), accounts=({**ACC, "secret": "tajne"},)))
    assert out["secret_ack"] == ["ftmo"] and drv.secrets == {"ftmo": "tajne"}
    assert "tajne" not in state.read_text(encoding="utf-8")
    assert rec.fragment()["secret_ack"] == ["ftmo"]

    # hub heslo už neposiela → ack sa neopakuje
    out = rec.run(desired(dep("d1")))
    assert out["secret_ack"] == []

    # heslo sa nedá uložiť → bez acku, chyba pri účte, nasadenie ide ďalej
    drv.fail["store_secret"] = "ftmo"
    out = rec.run(desired(dep("d1"), accounts=({**ACC, "secret": "x"},)))
    assert out["secret_ack"] == [] and "heslo" in rec.status()["accounts"]["ftmo"]["error"]
    assert out["applied"][0]["status"] == "ok"


def test_state_persists_and_vanished_deployment_is_removed(tmp_path: Path):
    state = tmp_path / "s.json"
    drv = FakeDriver()
    rec = Reconciler({"mt5": drv}, state)
    rec.run(desired(dep("d1"), dep("d2", symbol="EURUSD", active=False)))
    assert kinds(drv.calls, "remove_instance") == [("remove_instance", "ftmo", "d2")]
    assert kinds(drv.calls, "ensure_instance") == [("ensure_instance", "ftmo", ("d1",))]
    frag = rec.fragment()
    assert {a["deployment"]: (a["active"], a["status"]) for a in frag["applied"]} == {"d1": (True, "ok"), "d2": (False, "ok")}

    # nový reconciler nad tým istým súborom hlási to isté aj bez hubu (`run(None)` = starý hub)
    drv2 = FakeDriver()
    rec2 = Reconciler({"mt5": drv2}, state)
    assert rec2.fragment() == frag
    assert rec2.run(None) == frag and drv2.calls == []
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert [d["id"] for d in saved["desired"]["deployments"]] == ["d1", "d2"]

    # d1 z hubu zmizlo úplne → odstráni sa (účet je ešte v poslednom stave), inštancia účtu bez neho
    rec2.run(desired(accounts=(ACC,)))
    assert drv2.calls == [("remove_instance", "ftmo", "d1"), ("ensure_instance", "ftmo", ())]
    assert rec2.fragment()["applied"] == []

    # po reštarte bez zmeny sa nič nepíše: podpis je v stave na disku
    drv3 = FakeDriver()
    rec3 = Reconciler({"mt5": drv3}, state)
    rec3.run(desired(dep("d1")))
    assert [c[0] for c in drv3.calls] == ["ensure_profile", "write_control", "ensure_instance"]
    drv4 = FakeDriver()
    rec4 = Reconciler({"mt5": drv4}, state)
    rec4.run(desired(dep("d1")))
    assert [c[0] for c in drv4.calls] == ["ensure_instance"]


def test_zmena_instancie_odstrani_stary_control_bez_siroty(tmp_path: Path):
    """Stav si ku každému nasadeniu pamätá `instance` a cestu control súboru (len lokálne, do heartbeatu
    nejdú); keď sa id inštancie zmení (iný login účtu), starý control ide cez `remove_instance` drivera."""
    state = tmp_path / "s.json"
    drv = FakeDriver()
    rec = Reconciler({"mt5": drv}, state)
    rec.run(desired(dep("d1")))
    inst1 = instance_id("mt5", "1514750898-FTMO-Demo", "US100.cash", 1, "ibsnet")
    saved = json.loads(state.read_text(encoding="utf-8"))["applied"]["d1"]
    assert saved["instance"] == inst1 and saved["control"] == str(Path(f"/c/{inst1}.json"))
    assert not {"instance", "control", "sig"} & set(rec.fragment()["applied"][0])

    # účet zmenil login → iné id inštancie: starý control preč (pauza → zmazanie rieši driver), nový sa píše
    drv.calls.clear()
    acc2 = {**ACC, "login": "999"}
    inst2 = instance_id("mt5", "999-FTMO-Demo", "US100.cash", 1, "ibsnet")
    rec.run(desired(dep("d1"), accounts=(acc2,)))
    assert [c[0] for c in drv.calls] == ["remove_instance", "ensure_profile", "write_control", "ensure_instance"]
    assert drv.removed == [inst1] and drv.calls[2][2] == inst2
    assert json.loads(state.read_text(encoding="utf-8"))["applied"]["d1"]["instance"] == inst2
    # bez ďalšej zmeny sa nič neodstraňuje ani nepíše; cesta control ostáva v stave
    drv.calls.clear()
    rec.run(desired(dep("d1"), accounts=(acc2,)))
    assert [c[0] for c in drv.calls] == ["ensure_instance"] and drv.removed == [inst1]
    assert json.loads(state.read_text(encoding="utf-8"))["applied"]["d1"]["control"] == str(Path(f"/c/{inst2}.json"))
    # deaktivácia po ďalšej zmene loginu: odstráni sa stará aj nová inštancia
    drv.calls.clear()
    acc3 = {**ACC, "login": "555"}
    inst3 = instance_id("mt5", "555-FTMO-Demo", "US100.cash", 1, "ibsnet")
    rec.run(desired(dep("d1", active=False), accounts=(acc3,)))
    assert drv.removed == [inst1, inst2, inst3] and [c[0] for c in drv.calls] == ["remove_instance", "remove_instance", "ensure_instance"]


def test_deployment_dataclass_defaults_and_validation():
    d = Deployment.from_dict({"id": "x", "tf": "3", "mode": "divne"})
    assert d.tf == 3 and d.mode == "enabled" and d.active is True and d.config == {}
    with pytest.raises(ValueError) as e:
        d.validate()
    assert "stratégia" in str(e.value) and "symbol" in str(e.value) and "profil" in str(e.value)
    with pytest.raises(ValueError):
        Deployment.from_dict(dep("y", profile="..\\x")).validate()
    a = Account.from_dict({"id": "a", "platform": "mt5", "secret": ""})
    assert a.secret is None and a.portable is False


# --------------------------------------------------------------------------- #
# agent hubu: `live` v heartbeate a odpoveď → reconciler v pomalom kroku
# --------------------------------------------------------------------------- #


class FakeReconciler:
    def __init__(self) -> None:
        self.runs: list[dict] = []
        self.drivers = {"mt5": None}

    def run(self, desired):
        self.runs.append(desired)
        return self.fragment()

    def fragment(self):
        if not self.runs:
            return {"applied": [], "secret_ack": []}
        return {"applied": [{"deployment": "d1", "status": "ok"}], "secret_ack": ["ftmo"]}

    def status(self):
        return {"drivers": ["mt5"], "runs": len(self.runs)}


class FakeHttp:
    def __init__(self, live_response) -> None:
        self.live_response = live_response
        self.heartbeats: list[dict] = []

    def post(self, path, body=None):
        if path.endswith("/heartbeat"):
            self.heartbeats.append(body)
            return {"live": self.live_response} if self.live_response is not None else {}
        if path == "/api/live/events":
            return {"accepted": sum(len(b["events"]) for b in body["batches"])}
        return {}

    def post_bytes(self, path, data):
        return {}

    def get(self, path):
        return {}


class NoRunner:
    def snapshot(self):
        return []

    def job(self, run_id):
        return None


class NoStore:
    root = Path(".")

    def all(self):
        return []

    def get(self, run_id):
        return None


def _agent(tmp_path: Path, monkeypatch, http, reconciler):
    from tester.hub.agent import HubAgent
    from tester.hub.config import AgentConfig

    monkeypatch.setenv("TRADEBOT_NT_DIR", str(tmp_path / "nie-nt"))
    monkeypatch.setenv("TRADEBOT_MT5_COMMON", str(tmp_path / "nie-mt5"))
    spool = tmp_path / "spool"
    inst = instance_id("mt5", "1514750898-FTMO-Demo", "US100.cash", 1, "ibsnet")
    (spool / inst).mkdir(parents=True)
    ev = [
        {"seq": 1, "t": 1000, "k": "hello", "schema": 1, "platform": "mt5", "account": "1514750898-FTMO-Demo",
         "symbol": "US100.cash", "tf": 1, "strategy": "ibsnet", "profile": "p", "session": "abcd1234"},
        {"seq": 2, "t": 2000, "k": "bar", "bt": 1500, "o": 1, "h": 1, "l": 1, "c": 1, "v": 1, "ready": True},
        {"seq": 3, "t": 3000, "k": "control", "mode": "paused", "profile": "golden", "source": "control"},
    ]
    (spool / inst / "20260928-100000_abcd1234.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ev), encoding="utf-8")
    monkeypatch.setenv("TRADEBOT_LIVE_SPOOL", str(spool))
    cfg = AgentConfig(name="pc", hub_url="http://hub", token="t")
    agent = HubAgent(cfg, NoRunner(), NoStore(), http=http, state_path=tmp_path / "state.json",
                     config_path=tmp_path / "agent.json", live_cursor=tmp_path / "cursor.json",
                     reconciler=reconciler, apply_state=tmp_path / "apply.json", version="abc")
    return agent, inst


def test_agent_heartbeat_carries_live_and_response_drives_reconciler(tmp_path: Path, monkeypatch):
    wanted = {"accounts": [ACC], "deployments": [dep("d1")]}
    http = FakeHttp(wanted)
    rec = FakeReconciler()
    agent, inst = _agent(tmp_path, monkeypatch, http, rec)

    agent.tick()   # bez vlákien: heartbeat a hneď za ním pomalá práca (vrátane _apply_live)
    body = http.heartbeats[0]["live"]
    assert body["instances"] == [{"instance": inst, "session": "abcd1234", "last_t": 3000, "last_bar_ms": 1500,
                                  "mode": "paused", "profile": "golden", "ended": False}]
    assert body["applied"] == [] and body["secret_ack"] == [] and body["drivers"] == ["mt5"]
    assert rec.runs == [wanted]   # reconciler bežal v `work()`, nie v heartbeate

    agent.tick()
    body = http.heartbeats[1]["live"]
    assert body["applied"] == [{"deployment": "d1", "status": "ok"}] and body["secret_ack"] == ["ftmo"]
    assert rec.runs == [wanted, wanted]
    assert agent.live_status()["apply"] == {"drivers": ["mt5"], "runs": 2}
    assert agent.public()["live"]["apply"]["runs"] == 2

    # nová odpoveď bez zmeny sa aplikuje znova (hub posiela celý stav; idempotenciu rieši reconciler),
    # odpoveď bez `live` (starý hub) reconciler nevolá
    http.live_response = None
    agent.tick()
    assert len(rec.runs) == 2 and "live" in http.heartbeats[2]


def test_agent_survives_reconciler_failure(tmp_path: Path, monkeypatch):
    class Bad(FakeReconciler):
        def run(self, desired):
            raise RuntimeError("driver spadol")

    http = FakeHttp({"accounts": [], "deployments": []})
    agent, _ = _agent(tmp_path, monkeypatch, http, Bad())
    agent.tick()
    assert agent.last_error is None and len(http.heartbeats) == 1
    agent.tick()
    assert len(http.heartbeats) == 2


# --------------------------------------------------------------------------- #
# celá cesta: hub (DeployStore) ↔ agent ↔ Reconciler ↔ driver
# --------------------------------------------------------------------------- #


class HubHttp:
    """`HubHttp` nad TestClientom — agent nepozná rozdiel."""

    def __init__(self, client, token: str) -> None:
        self.c, self.h, self.timeout = client, {"Authorization": f"Bearer {token}"}, 30

    def _raise(self, r):
        from tester.hub.client import HubError

        if r.status_code >= 400:
            raise HubError(r.status_code, r.text)

    def get(self, path):
        r = self.c.get(path, headers=self.h); self._raise(r); return r.json()

    def get_bytes(self, path):
        r = self.c.get(path, headers=self.h); self._raise(r); return r.content

    def post(self, path, body=None):
        r = self.c.post(path, json=body or {}, headers=self.h); self._raise(r); return r.json()

    def post_bytes(self, path, data):
        r = self.c.post(path, content=data, headers={**self.h, "Content-Type": "application/zip"}); self._raise(r); return r.json()


def test_hub_agent_reconciler_driver_end_to_end(tmp_path: Path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.hub.agent import HubAgent
    from tester.hub.config import AgentConfig
    from tester.hub.server import HubState, create_hub_app
    from tradebot.live.deploy import DeployStore
    from tradebot.live.store import LiveStore

    monkeypatch.setenv("TRADEBOT_NT_DIR", str(tmp_path / "nie-nt"))
    monkeypatch.setenv("TRADEBOT_MT5_COMMON", str(tmp_path / "nie-mt5"))
    monkeypatch.delenv("TRADEBOT_LIVE_SPOOL", raising=False)
    state = HubState(tmp_path / "hub", token="hlavny")
    t_agent = state.add_token("trade-pc")
    live = LiveStore(tmp_path / "hub" / "live.sqlite")
    deploy = DeployStore(live.path, config_resolver=lambda s, p: {"rrRatio": 3.0, "p": p}, strategy_check=lambda k: k)
    c = TestClient(create_hub_app(state, live_store=live, deploy_store=deploy))
    H = {"Authorization": "Bearer hlavny"}
    c.post("/api/live/accounts", json={"agent": "trade-pc", "platform": "mt5", "label": "IC", "login": "1", "server": "S",
                                       "password": "tajne"}, headers=H)
    d = c.post("/api/live/deployments", json={"account": "ic", "strategy": "ibsnet", "symbol": "NAS100", "tf": 3, "profile": "p1"},
               headers=H).json()

    drv = FakeDriver()
    rec = Reconciler({"mt5": drv}, tmp_path / "apply.json")
    agent = HubAgent(AgentConfig(name="trade-pc", hub_url="http://hub", token=t_agent), NoRunner(), NoStore(),
                     http=HubHttp(c, t_agent), state_path=tmp_path / "state.json", config_path=tmp_path / "agent.json",
                     live_cursor=tmp_path / "cursor.json", reconciler=rec, version="abc")

    agent.tick()   # heartbeat prinesie účet s heslom a nasadenie → reconciler v `work()` → driver
    assert drv.secrets == {"ic": "tajne"}
    assert [k[0] for k in drv.calls] == ["store_secret", "ensure_profile", "write_control", "ensure_instance"]
    assert drv.calls[2][2] == d["instance"] and drv.calls[2][3] == "paused"      # nové nasadenie štartuje pauznuté
    assert c.get("/api/live/accounts/ic", headers=H).json()["secret_pending"] is True   # ack ide až ďalším heartbeatom

    agent.tick()
    assert c.get("/api/live/accounts/ic", headers=H).json()["secret_pending"] is False
    dep = c.get(f"/api/live/deployments/{d['id']}", headers=H).json()
    assert dep["applied"]["status"] == "ok" and dep["applied"]["config_hash"] == d["config_hash"] and dep["applied"]["mode"] == "paused"
    assert state.live_state("trade-pc")["drivers"] == ["mt5"]

    # zapnutie z hubu → len control; zrušenie → remove_instance a inštancia bez neho
    c.patch(f"/api/live/deployments/{d['id']}", json={"mode": "enabled"}, headers=H)
    drv.calls.clear()
    agent.tick()
    assert [k[0] for k in drv.calls] == ["ensure_profile", "write_control", "ensure_instance"] and drv.calls[1][3] == "enabled"
    c.delete(f"/api/live/deployments/{d['id']}", headers=H)
    drv.calls.clear()
    agent.tick()
    assert drv.calls == [("remove_instance", "ic", d["id"]), ("ensure_instance", "ic", ())]
    agent.tick()
    assert c.get(f"/api/live/deployments/{d['id']}", headers=H).json()["applied"]["status"] == "ok"
