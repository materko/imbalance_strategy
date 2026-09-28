"""Nový kód na obchodnom stroji (docs/LIVE.md, fáza 2c): `tradebot.live.update.CodeUpdater` s falošnými
drivermi a falošným gitom — brána (pauza + bez pozície), `force`, pull len keď commit chýba, chyby po
platformách oddelene, markery `installed.json`; a agent hubu, ktorý cieľ z heartbeatu vezme, výsledok
pošle v `live.code_update` a hotový cieľ neopakuje."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.live.drivers.base import Account, Driver
from tradebot.live.schema import instance_id
from tradebot.live.update import CodeUpdater, gate_reasons, position_from_spool

ACC_MT5 = {"id": "ftmo", "platform": "mt5", "label": "FTMO", "login": "1514750898", "server": "FTMO-Demo"}
ACC_NT = {"id": "sim", "platform": "ninjatrader", "label": "Sim", "login": "Sim101", "server": "Simulated Data Feed"}
INST_MT5 = instance_id("mt5", "1514750898-FTMO-Demo", "US100.cash", 1, "ibsnet")
INST_NT = instance_id("ninjatrader", "Sim101", "MNQ", 3, "ibsnet")


def dep(i: str, **over) -> dict:
    d = {"id": i, "account": "ftmo", "strategy": "ibsnet", "symbol": "US100.cash", "tf": 1, "profile": "p",
         "config": {}, "config_hash": "h", "mode": "paused", "active": True, "instance": INST_MT5}
    d.update(over)
    return d


class FakeDriver(Driver):
    """Marker v tmp súbore; `install_code` ho zapíše (alebo padne, keď má)."""

    def __init__(self, platform: str, marker: Path, fail: str | None = None) -> None:
        self.platform = platform
        self.marker = marker
        self.fail = fail
        self.calls: list[tuple] = []

    def available(self): return True
    def store_secret(self, account, password): pass
    def ensure_profile(self, deployment): return Path("x")
    def write_control(self, deployment): return Path("x")
    def ensure_instance(self, account, deployments): pass
    def remove_instance(self, account, deployment): pass
    def status(self, account): return {"installed": self.installed_version()}

    def installed_version(self):
        try:
            return json.loads(self.marker.read_text(encoding="utf-8"))["version"]
        except (OSError, ValueError, KeyError):
            return None

    def install_code(self, version, accounts):
        self.calls.append(("install_code", version, tuple(a.id for a in accounts)))
        if self.fail:
            raise RuntimeError(self.fail)
        self.marker.parent.mkdir(parents=True, exist_ok=True)
        self.marker.write_text(json.dumps({"version": version}), encoding="utf-8")
        return {"compiled": True}


class FakeGit:
    def __init__(self, head: str, have: set[str] | None = None, pull_adds: set[str] | None = None) -> None:
        self.head, self.have = head, set(have or {head})
        self.pull_adds = pull_adds or set()
        self.pulls = 0

    def version(self): return self.head
    def has_version(self, c): return not c or c in self.have

    def pull(self):
        self.pulls += 1
        if self.pull_adds:
            self.have |= self.pull_adds
            self.head = sorted(self.pull_adds)[-1]
        return {"ok": True, "output": "Fast-forward"}


class FakeReconciler:
    def __init__(self, deployments: list[dict], accounts: list[dict], applied: dict | None = None) -> None:
        self.state = {"desired": {"accounts": accounts, "deployments": deployments}, "applied": applied or {}}
        self.drivers = {}


def _spool(tmp_path: Path, instance: str, events: list[dict], name: str = "20260928-100000_abcd1234.jsonl") -> Path:
    root = tmp_path / "spool"
    (root / instance).mkdir(parents=True, exist_ok=True)
    (root / instance / name).write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return root


HELLO = {"seq": 1, "t": 1000, "k": "hello", "schema": 1, "platform": "mt5", "account": "1514750898-FTMO-Demo",
         "symbol": "US100.cash", "tf": 1, "strategy": "ibsnet", "profile": "p", "session": "abcd1234"}


def _fill(seq: int, side: str, qty: float, ident: str = "L-1") -> dict:
    return {"seq": seq, "t": 1000 + seq, "k": "fill", "ft": 1000 + seq, "id": ident, "side": side, "exit": "", "price": 1.0,
            "qty": qty, "ready": True}


def _updater(tmp_path: Path, *, drivers=None, git=None, deployments=None, accounts=None, applied=None, roots=None):
    drivers = drivers if drivers is not None else {"mt5": FakeDriver("mt5", tmp_path / "m" / "mt5.json")}
    rec = FakeReconciler(deployments if deployments is not None else [dep("d1")],
                         accounts if accounts is not None else [ACC_MT5], applied)
    return CodeUpdater(drivers, git=git, reconciler=rec, roots=lambda: list(roots or []), clock=lambda: 5.0), drivers


# --------------------------------------------------------------------------- #
# pozícia a brána
# --------------------------------------------------------------------------- #


def test_position_from_spool_a_brana(tmp_path: Path):
    assert position_from_spool([tmp_path / "nie"], INST_MT5) is None
    root = _spool(tmp_path, INST_MT5, [HELLO, _fill(2, "in", 2), _fill(3, "out", 1)])
    assert position_from_spool([root], INST_MT5) == 1.0
    # druhý súbor (nová session) výstup dokončí — pozícia sa počíta cez všetky súbory inštancie
    _spool(tmp_path, INST_MT5, [{**HELLO, "session": "ef012345"}, _fill(2, "out", 1)], name="20260928-110000_ef012345.jsonl")
    assert position_from_spool([root], INST_MT5) == 0.0

    stav = [{"instance": INST_MT5, "mode": "paused"}]
    assert gate_reasons([dep("d1")], stav, [root]) == []
    assert gate_reasons([dep("d1", active=False)], [], [tmp_path / "nie"]) == []            # neaktívne sa nepočíta
    r = gate_reasons([dep("d1")], [{"instance": INST_MT5, "mode": "enabled"}], [root])
    assert len(r) == 1 and "obchoduje" in r[0] and "enabled" in r[0]
    r = gate_reasons([dep("d1")], [], [tmp_path / "nie"])                                   # bez spoolu: režim z hubu, pozícia neznáma
    assert len(r) == 1 and "neznáma" in r[0]
    # spool bez `control` udalosti: režim z toho, čo reconciler zapísal, inak z nasadenia
    assert gate_reasons([dep("d1", mode="enabled")], [{"instance": INST_MT5, "mode": None}], [root],
                        applied={"d1": {"mode": "paused"}}) == []
    assert len(gate_reasons([dep("d1", mode="enabled")], [{"instance": INST_MT5, "mode": None}], [root])) == 1
    _spool(tmp_path, INST_MT5, [{**HELLO, "session": "ff012345"}, _fill(2, "in", 1, "S-9")], name="20260928-120000_ff012345.jsonl")
    r = gate_reasons([dep("d1")], stav, [root])
    assert len(r) == 1 and "otvorená pozícia (1)" in r[0]


# --------------------------------------------------------------------------- #
# CodeUpdater
# --------------------------------------------------------------------------- #


def test_noop_ked_marker_sedi_a_force_ho_prebije(tmp_path: Path):
    upd, drivers = _updater(tmp_path, git=FakeGit("abc1234"), roots=[tmp_path / "nie"])
    drivers["mt5"].marker.parent.mkdir(parents=True)
    drivers["mt5"].marker.write_text(json.dumps({"version": "abc1234"}), encoding="utf-8")
    r = upd.run({"version": "abc1234", "force": False, "ts": 1.0})
    assert r["status"] == "ok" and r["noop"] is True and drivers["mt5"].calls == [] and r["installed"] == {"mt5": "abc1234"}
    assert r["platforms"] == {"mt5": {"status": "ok", "installed": "abc1234", "noop": True}}
    # force = urobí sa znova, brána sa preskočí (bez spoolu by inak blokovalo)
    r = upd.run({"version": "abc1234", "force": True, "ts": 2.0})
    assert r["status"] == "ok" and not r.get("noop") and drivers["mt5"].calls == [("install_code", "abc1234", ("ftmo",))]
    assert r["pulled"] is False and r["code_changed"] is False and r["reasons"] == []


def test_brana_blokuje_a_nic_neinstaluje(tmp_path: Path):
    root = _spool(tmp_path, INST_MT5, [HELLO, {"seq": 2, "t": 2000, "k": "control", "mode": "enabled", "profile": "p", "source": "control"}])
    upd, drivers = _updater(tmp_path, git=FakeGit("abc1234"), roots=[root])
    r = upd.run({"version": "abc1234", "force": False, "ts": 1.0})
    assert r["status"] == "blocked" and "obchoduje" in r["reasons"][0] and r["error"].startswith("blokované")
    assert drivers["mt5"].calls == [] and r["platforms"] == {} and upd.last is r
    # pauza v spoole → prejde
    _spool(tmp_path, INST_MT5, [HELLO, {"seq": 2, "t": 2000, "k": "control", "mode": "paused", "profile": "p", "source": "control"}])
    r = upd.run({"version": "abc1234", "force": False, "ts": 2.0})
    assert r["status"] == "ok" and drivers["mt5"].installed_version() == "abc1234"


def test_pull_len_ked_commit_chyba_a_chyba_ked_nepride(tmp_path: Path):
    git = FakeGit("aaa1111", have={"aaa1111"}, pull_adds={"bbb2222"})
    upd, drivers = _updater(tmp_path, git=git, roots=[tmp_path / "nie"])
    r = upd.run({"version": "aaa1111", "force": True, "ts": 1.0})
    assert r["status"] == "ok" and git.pulls == 0 and r["pulled"] is False and r["code_changed"] is False
    r = upd.run({"version": "bbb2222", "force": True, "ts": 2.0})
    assert r["status"] == "ok" and git.pulls == 1 and r["pulled"] is True and r["code_changed"] is True
    assert drivers["mt5"].calls[-1] == ("install_code", "bbb2222", ("ftmo",))
    # commit, ktorý ani pull neprinesie: chyba, žiadna inštalácia
    n = len(drivers["mt5"].calls)
    r = upd.run({"version": "ccc3333", "force": True, "ts": 3.0})
    assert r["status"] == "error" and "ccc3333" in r["error"] and "git pull" in r["error"] and git.pulls == 2
    assert len(drivers["mt5"].calls) == n


def test_chyby_po_platformach_oddelene_a_markery(tmp_path: Path):
    drivers = {"mt5": FakeDriver("mt5", tmp_path / "m" / "mt5.json", fail="TradeBot.dll je zamknutá"),
               "ninjatrader": FakeDriver("ninjatrader", tmp_path / "n" / "nt.json")}
    upd, _ = _updater(tmp_path, drivers=drivers, git=FakeGit("abc1234"), accounts=[ACC_MT5, ACC_NT],
                      deployments=[dep("d1"), dep("d2", account="sim", symbol="MNQ", tf=3, instance=INST_NT)],
                      roots=[tmp_path / "nie"])
    r = upd.run({"version": "abc1234", "force": True, "ts": 1.0})
    assert r["status"] == "error" and r["error"] == "mt5: TradeBot.dll je zamknutá"
    assert r["platforms"]["mt5"] == {"status": "error", "error": "TradeBot.dll je zamknutá", "installed": None}
    assert r["platforms"]["ninjatrader"] == {"status": "ok", "error": None, "compiled": True, "installed": "abc1234"}
    assert r["installed"] == {"mt5": None, "ninjatrader": "abc1234"}
    # každý driver dostal len účty svojej platformy
    assert drivers["mt5"].calls == [("install_code", "abc1234", ("ftmo",))]
    assert drivers["ninjatrader"].calls == [("install_code", "abc1234", ("sim",))]
    # bez drivera / bez verzie: chyba, nie výnimka
    assert CodeUpdater({}, clock=lambda: 1.0).run({"version": "x"})["status"] == "error"
    assert upd.run({"version": "", "force": True})["status"] == "error"


# --------------------------------------------------------------------------- #
# agent: cieľ z heartbeatu → `live.code_update` a `live.installed`, opakovanie
# --------------------------------------------------------------------------- #


class FakeUpdater:
    def __init__(self, status: str = "ok") -> None:
        self.status = status
        self.runs: list[dict] = []
        self.marker = "old1234"

    def installed(self):
        return {"mt5": self.marker}

    def run(self, target):
        self.runs.append(dict(target))
        if self.status == "ok":
            self.marker = target["version"]
        return {"version": target["version"], "status": self.status, "error": None if self.status == "ok" else "blokované: x",
                "reasons": [] if self.status == "ok" else ["x"], "platforms": {}, "ts": 1.0, "code_changed": False}


class FakeHttp:
    def __init__(self) -> None:
        self.live: dict | None = {"accounts": [], "deployments": []}
        self.heartbeats: list[dict] = []

    def post(self, path, body=None):
        if path.endswith("/heartbeat"):
            self.heartbeats.append(body)
            return {"live": self.live} if self.live is not None else {}
        return {}

    def post_bytes(self, path, data): return {}
    def get(self, path): return {}


class NoRunner:
    def snapshot(self): return []
    def job(self, run_id): return None


class NoStore:
    root = Path(".")
    def all(self): return []
    def get(self, run_id): return None


class Clock:
    def __init__(self) -> None: self.t = 1000.0
    def __call__(self) -> float: return self.t


def _agent(tmp_path: Path, monkeypatch, http, updater):
    from tester.hub import agent as agent_mod
    from tester.hub.agent import HubAgent
    from tester.hub.config import AgentConfig

    monkeypatch.setenv("TRADEBOT_NT_DIR", str(tmp_path / "nie-nt"))
    monkeypatch.setenv("TRADEBOT_MT5_COMMON", str(tmp_path / "nie-mt5"))
    monkeypatch.setenv("TRADEBOT_LIVE_SPOOL", str(tmp_path / "spool-nie"))
    monkeypatch.setattr(agent_mod.gitcode, "version", lambda: "abc")
    clock = Clock()
    cfg = AgentConfig(name="pc", hub_url="http://hub", token="t")

    class Rec:
        drivers = {"mt5": None}
        def run(self, desired): return self.fragment()
        def fragment(self): return {"applied": [], "secret_ack": []}
        def status(self): return {}

    agent = HubAgent(cfg, NoRunner(), NoStore(), http=http, state_path=tmp_path / "state.json",
                     config_path=tmp_path / "agent.json", live_cursor=tmp_path / "cursor.json",
                     reconciler=Rec(), apply_state=tmp_path / "apply.json", version="abc", clock=clock,
                     updater=updater)
    return agent, clock


def test_agent_vezme_ciel_posle_vysledok_a_hotovy_neopakuje(tmp_path: Path, monkeypatch):
    http, upd = FakeHttp(), FakeUpdater()
    agent, clock = _agent(tmp_path, monkeypatch, http, upd)
    agent.tick()
    assert http.heartbeats[0]["live"]["installed"] == {"mt5": "old1234"} and http.heartbeats[0]["live"]["code_update"] is None
    assert upd.runs == []
    http.live = {"accounts": [], "deployments": [], "code_target": {"version": "new5678", "force": False, "requested_by": "rasto", "ts": 1.0}}
    agent.tick()   # heartbeat prinesie cieľ → work() (bez vlákien hneď) → updater
    assert upd.runs == [{"version": "new5678", "force": False, "requested_by": "rasto", "ts": 1.0}]
    assert agent.updating is None and agent.public()["code_target"]["version"] == "new5678"
    agent.tick()
    body = http.heartbeats[2]["live"]
    assert body["installed"] == {"mt5": "new5678"} and body["code_update"]["status"] == "ok" and body["code_update"]["version"] == "new5678"
    assert len(upd.runs) == 1                  # ten istý cieľ sa po `ok` neopakuje, aj keď ho hub ešte posiela
    http.live = {"accounts": [], "deployments": []}
    agent.tick()
    assert agent.public()["code_target"] is None and len(upd.runs) == 1
    # nový cieľ (iný čas) ide hneď; `force` v tele prejde
    http.live = {"accounts": [], "deployments": [], "code_target": {"version": "new5678", "force": True, "requested_by": "r", "ts": 2.0}}
    agent.tick()
    assert len(upd.runs) == 2 and upd.runs[-1]["force"] is True
    assert agent.needs_restart is False        # kód procesu sa nezmenil (version == start_version)


def test_agent_blokovany_ciel_skusa_o_minutu_a_pocas_vypoctu_caka(tmp_path: Path, monkeypatch):
    from tester.hub.agent import CODE_RETRY_BLOCKED

    http, upd = FakeHttp(), FakeUpdater(status="blocked")
    agent, clock = _agent(tmp_path, monkeypatch, http, upd)
    http.live = {"accounts": [], "deployments": [], "code_target": {"version": "v2", "force": False, "requested_by": "r", "ts": 1.0}}
    agent.tick()
    assert len(upd.runs) == 1 and agent.public()["code_update"]["status"] == "blocked"
    agent.tick()
    assert len(upd.runs) == 1                  # do minúty sa neskúša
    clock.t += CODE_RETRY_BLOCKED + 1
    agent.tick()
    assert len(upd.runs) == 2
    # počas výpočtu hubu sa kód nemení: hlási sa blokované s dôvodom, updater sa nevolá
    from types import SimpleNamespace

    agent.state.computing["j1"] = {"run_id": "r1", "estimate_seconds": 60.0}
    agent.runner.job = lambda run_id: SimpleNamespace(status="running", settings={}, log_lines=[], started=None)
    clock.t += CODE_RETRY_BLOCKED + 1
    agent.tick()
    cu = agent.public()["code_update"]
    assert len(upd.runs) == 2 and cu["status"] == "blocked" and "výpočt" in cu["reasons"][0]
    agent.tick()   # ďalší heartbeat to odnesie
    assert http.heartbeats[-1]["live"]["code_update"]["reasons"] == cu["reasons"]


def test_agent_po_zmene_kodu_hlasi_restart(tmp_path: Path, monkeypatch):
    class Pulling(FakeUpdater):
        def run(self, target):
            out = super().run(target)
            out["code_changed"] = True
            return out

    http, upd = FakeHttp(), Pulling()
    agent, clock = _agent(tmp_path, monkeypatch, http, upd)
    http.live = {"accounts": [], "deployments": [], "code_target": {"version": "v9", "force": True, "requested_by": "r", "ts": 1.0}}
    agent.tick()
    assert agent.needs_restart is True and agent.code_changed is True
    agent.tick()
    assert http.heartbeats[-1]["needs_restart"] is True and http.heartbeats[-1]["live"]["code_update"]["needs_restart"] is True
