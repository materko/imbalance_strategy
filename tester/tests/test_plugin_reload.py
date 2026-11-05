"""Nový kód pluginov bez reštartu (docs/HUB.md, „Pluginy“ — „Nový kód pluginu“, „Pluginy agenta“): pravidlo
„zmena len v adresári pluginu“, reload balíka z disku, `PluginHost.reload` hubu, samoaktualizácia hubu bez drainu,
`AgentPluginHost` a `PluginUpdater` agenta (z disku aj pull na obchodnom stroji) a odtlačok kódu webapp."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from tester.hub.agent_plugins import AgentPlugin, AgentPluginContext, AgentPluginHost, PluginUpdater, discover
from tester.hub.pluginreload import AGENT_PLUGINS, HUB_PLUGINS, plugin_only, reload_package
from tester.hub.plugins import HubPlugin, PluginHost
from tester.hub.update import Updater
from tester.webapp.__main__ import _plugin_file


def test_len_plugin_rozhranie_a_neutralne_subory():
    tg = "tester/hub/agent_plugins/telegram/"
    assert plugin_only([tg + "reports.py", tg + "service.py"], AGENT_PLUGINS) == {"telegram"}
    # dokumenty, testy, história behov a živé dáta proces nenačítava
    assert plugin_only([tg + "perf.py", "docs/LIVE.md", "README.md", "tester/tests/test_x.py",
                        "tester/runs/20261104-1/run.json", "data/live/x.feather"], AGENT_PLUGINS) == {"telegram"}
    assert plugin_only(["docs/HUB.md"], AGENT_PLUGINS) == set()
    # rozhranie (koreň balíka pluginov), iný kód, klient Telegramu → reštart
    assert plugin_only([tg + "x.py", "tester/hub/agent_plugins/base.py"], AGENT_PLUGINS) is None
    assert plugin_only([tg + "x.py", "tester/hub/agent.py"], AGENT_PLUGINS) is None
    assert plugin_only([tg + "x.py", "tradebot/live/telegram.py"], AGENT_PLUGINS) is None
    assert plugin_only(["tester/hub/agent_plugins/_spolocne/x.py"], AGENT_PLUGINS) is None
    assert plugin_only(None, AGENT_PLUGINS) is None
    # hub: plugin hubu áno, plugin agenta pre hub nie je plugin
    assert plugin_only(["tester/hub/plugins/watchdog/plugin.py"], HUB_PLUGINS) == {"watchdog"}
    assert plugin_only([tg + "x.py"], HUB_PLUGINS) is None


def test_reload_package_nacita_novy_kod_z_disku(tmp_path: Path, monkeypatch):
    pkg = tmp_path / "pr_balik"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .mod import X\n", encoding="utf-8")
    (pkg / "mod.py").write_text("X = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    import pr_balik

    assert pr_balik.X == 1
    (pkg / "mod.py").write_text("X = 2  # novy kod\n", encoding="utf-8")
    assert reload_package("pr_balik").X == 2 and sys.modules["pr_balik.mod"].X == 2


class _Pocitadlo(HubPlugin):
    interval = 1.0
    teardowns = 0

    def tick(self) -> None:
        self.ctx.dir.mkdir(parents=True, exist_ok=True)

    def teardown(self) -> None:
        type(self).teardowns += 1


def test_hub_plugin_host_reload_zastavi_vlakno_a_spusti_nove(tmp_path: Path):
    host = PluginHost(tmp_path, None, None, classes={"pocitadlo": _Pocitadlo})
    host.start()
    stary = host.slots["pocitadlo"]
    assert host.reload({"pocitadlo"}) is True
    novy = host.slots["pocitadlo"]
    assert novy is not stary and novy.plugin is not stary.plugin and not stary.thread.is_alive()
    assert novy.thread.is_alive() and novy.reloads == 1 and _Pocitadlo.teardowns == 1
    assert host.status()[0]["reloads"] == 1
    assert host.brief()["pocitadlo"]["running"] and host.brief()["pocitadlo"]["error"] == ""
    host.stop()


def test_samoaktualizacia_hubu_len_pluginy_bez_restartu():
    reloady, quit_ = [], []
    verzia = ["aaa"]
    state = SimpleNamespace(jobs={"j": {"id": "j", "status": "running"}},
                            plugins=SimpleNamespace(reload=lambda m: reloady.append(set(m)) or True))
    zmeny = {("aaa", "bbb"): ["tester/hub/plugins/ff_calendar/plugin.py", "docs/HUB.md"],
             ("bbb", "ccc"): ["tester/hub/plugins/ff_calendar/plugin.py", "tester/hub/state.py"]}
    u = Updater(state, pull=lambda: {"ok": True}, version=lambda: verzia[0], quit=lambda: quit_.append(1),
                changed=lambda a, b: zmeny.get((a, b)))
    verzia[0] = "bbb"
    assert u.tick() is False and reloady == [{"ff_calendar"}] and not quit_
    assert u.start_version == "bbb" and u.pending is None and u.public()["plugins_reloaded"]["plugins"] == ["ff_calendar"]
    # zmena mimo pluginov → po starom: čaká na dobehnutie výpočtu a reštart
    verzia[0] = "ccc"
    assert u.tick() is False and u.pending == "ccc" and reloady == [{"ff_calendar"}]
    state.jobs.clear()
    assert u.tick() is True and quit_ == [1]


def test_samoaktualizacia_hubu_reload_zlyhal_ide_po_starom():
    state = SimpleNamespace(jobs={}, plugins=SimpleNamespace(reload=lambda m: False))
    verzia = ["aaa"]
    quit_ = []
    u = Updater(state, pull=lambda: {"ok": True}, version=lambda: verzia[0], quit=lambda: quit_.append(1),
                changed=lambda a, b: ["tester/hub/plugins/livedata/plugin.py"])
    verzia[0] = "bbb"
    assert u.tick() is True and quit_ == [1]


class _Agentovy(AgentPlugin):
    interval = 0.05
    ticks = 0

    def setup(self, ctx: AgentPluginContext) -> None:
        self.ctx = ctx
        self.prekrytia = [{"instance": "i1", "mode": "paused", "ts": 1.0}]
        self.desired_seen: list = []

    def tick(self) -> None:
        type(self).ticks += 1

    def status(self):
        return {"ok": True}

    def overrides(self):
        return list(self.prekrytia)

    def drop_override(self, instance: str) -> None:
        self.prekrytia = [o for o in self.prekrytia if o["instance"] != instance]

    def desired(self, desired, now) -> None:
        self.desired_seen.append(desired)


def test_agent_plugin_host_vlakna_prekrytia_a_reload():
    kontexty: list[AgentPluginContext] = []

    def kontext(name: str, stopping: threading.Event) -> AgentPluginContext:
        kontexty.append(AgentPluginContext(name, agent_name="nas", stopping=stopping))
        return kontexty[-1]

    host = AgentPluginHost(kontext, classes={"x": _Agentovy})
    host.start()
    deadline = time.time() + 5
    while _Agentovy.ticks < 2 and time.time() < deadline:
        time.sleep(0.02)
    assert _Agentovy.ticks >= 2 and host.status()["x"]["status"] == {"ok": True}
    assert host.overrides() == [{"instance": "i1", "mode": "paused", "ts": 1.0, "plugin": "x"}]
    host.desired({"deployments": []}, 5.0)
    assert host.slots["x"].plugin.desired_seen == [{"deployments": []}]
    host.drop_override("x", "i1")
    assert host.overrides() == []
    stary_ctx = kontexty[-1]
    assert host.reload(["x"]) is True
    assert stary_ctx.stopping.is_set() and not kontexty[-1].stopping.is_set()
    assert host.status()["x"]["reloads"] == 1 and host.status()["x"]["running"]
    b = host.brief()["x"]   # heartbeat → karta Hub, bez volania pluginu
    assert b["running"] and b["active"] and b["error"] == "" and set(b) == {"title", "running", "active", "error"}
    host.stop()
    assert not host.slots["x"].thread.is_alive()


def test_agent_plugin_telegram_sa_najde_a_nacita():
    assert "telegram" in discover()
    host = AgentPluginHost(lambda n, s: AgentPluginContext(n, stopping=s), names=["telegram"])
    st = host.status()["telegram"]
    assert st["load_error"] == "" and st["title"] == "Telegram" and st["status"] is None   # bez configu nič
    assert host.brief()["telegram"]["active"] is False      # stroj ho nepoužíva — karta Hub ho neukáže
    host.slots["telegram"].plugin.svc = object()
    assert host.brief()["telegram"]["active"] is True
    stary = host.slots["telegram"].plugin
    assert host.reload(["telegram"]) is True                     # nový import balíka z disku
    novy = host.slots["telegram"].plugin
    assert host.status()["telegram"]["load_error"] == "" and type(novy) is not type(stary)
    assert type(novy).__module__ == "tester.hub.agent_plugins.telegram.plugin"


def _updater(host, verzia, zmeny, **kw):
    return PluginUpdater(host, "aaa", version=lambda: verzia[0],
                         changed=lambda a, b, remote_side=False: zmeny.get((a, b)), **kw)


def test_plugin_updater_z_disku_reload_a_zmena_rozhrania():
    reloady = []
    host = SimpleNamespace(reload=lambda m: reloady.append(set(m)) or True)
    verzia = ["aaa"]
    zmeny = {("aaa", "bbb"): [AGENT_PLUGINS + "telegram/reports.py"],
             ("bbb", "ccc"): [AGENT_PLUGINS + "telegram/reports.py", AGENT_PLUGINS + "base.py"]}
    u = _updater(host, verzia, zmeny)
    assert u.tick() is None and reloady == []           # nič nové
    verzia[0] = "bbb"
    assert u.tick() == "bbb" and reloady == [{"telegram"}] and u.loaded == "bbb"
    verzia[0] = "ccc"                                    # rozhranie → reštart po starom, diff sa nepočíta znova
    volania = []
    u.changed = lambda a, b, remote_side=False: volania.append((a, b)) or zmeny.get((a, b))
    assert u.tick() is None and u.tick() is None and volania == [("bbb", "ccc")] and u.loaded == "bbb"


def test_plugin_updater_obchodny_stroj_si_pullne_len_pluginy():
    reloady, pully = [], []
    host = SimpleNamespace(reload=lambda m: reloady.append(set(m)) or True)
    verzia = ["aaa"]
    zmeny = {("HEAD", "origin/main"): [AGENT_PLUGINS + "telegram/service.py", "tester/runs/r/run.json"],
             ("aaa", "bbb"): [AGENT_PLUGINS + "telegram/service.py", "tester/runs/r/run.json"]}
    t = [1000.0]

    def pull():
        pully.append(1)
        verzia[0] = "bbb"
        return {"ok": True}

    u = _updater(host, verzia, zmeny, can_pull=lambda: True, pull=pull, fetch=lambda b: True,
                 interval=300, clock=lambda: t[0])
    assert u.tick() == "bbb" and pully == [1] and reloady == [{"telegram"}]
    # do intervalu sa nefetchuje znova; potom áno, ale origin už nič nové nemá
    zmeny[("HEAD", "origin/main")] = []
    assert u.tick() is None and pully == [1]
    t[0] += 301
    assert u.tick() is None and pully == [1]
    # origin mení aj jadro → agent nič neťahá sám (ide to cez nasadenie kódu s bránou)
    zmeny[("HEAD", "origin/main")] = [AGENT_PLUGINS + "telegram/service.py", "tradebot/live/deploy.py"]
    t[0] += 301
    assert u.tick() is None and pully == [1]
    # necommitnutý kód na stroji → tiež nie
    zmeny[("HEAD", "origin/main")] = [AGENT_PLUGINS + "telegram/service.py"]
    u.dirty = lambda: ["tester/hub/agent.py"]
    t[0] += 301
    assert u.tick() is None and pully == [1]
    # mimo obchodného stroja (can_pull False) sa nefetchuje vôbec
    u.dirty, u.can_pull = (lambda: []), (lambda: False)
    u.fetch = lambda b: (_ for _ in ()).throw(AssertionError("fetch"))
    t[0] += 301
    assert u.tick() is None


def test_odtlacok_webapp_ignoruje_kod_pluginov_nie_rozhranie():
    assert _plugin_file("tester/hub/agent_plugins/telegram/service.py")
    assert _plugin_file("tester/hub/plugins/watchdog/plugin.py")
    assert not _plugin_file("tester/hub/agent_plugins/base.py")
    assert not _plugin_file("tester/hub/plugins/__init__.py")
    assert not _plugin_file("tester/hub/agent.py")
