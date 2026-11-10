"""Pluginy hubu (`tester.hub.plugins`, docs/HUB.md, „Pluginy“): host, kalendár ForexFactory, strážca."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from tester.hub.plugins import HubPlugin, NotifyError, PluginHost, discover
from tester.hub.plugins.ff_calendar.alerts import CalendarConfig, remind_offsets
from tester.hub.plugins.ff_calendar.feed import feed_week, ny_week, parse_feed
from tester.hub.plugins.ff_calendar.plugin import RETRY_FAIL, STALE_AFTER, FFCalendar
from tester.hub.plugins.watchdog.plugin import OFFLINE_GRACE, PLUGIN_GRACE, SHIP_GRACE, Watchdog

FEED = [
    {"title": "CPI m/m", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "impact": "High",
     "forecast": "0.6%", "previous": "0.4%"},
    {"title": "Core CPI m/m", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "impact": "High",
     "forecast": "0.2%", "previous": "0.3%"},
    {"title": "Retail Sales m/m", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "impact": "Medium",
     "forecast": "", "previous": ""},
    {"title": "GDP m/m", "country": "GBP", "date": "2026-10-15T02:00:00-04:00", "impact": "High",
     "forecast": "0.1%", "previous": ""},
    {"title": "Bank Holiday", "country": "JPY", "date": "2026-10-11T19:00:00-04:00", "impact": "Holiday"},
    {"title": "Zlý čas", "country": "EUR", "date": "zajtra", "impact": "High"},
]
#: CPI = 12:30 UTC = 14:30 v Bratislave (letný čas)
CPI = datetime(2026, 10, 14, 12, 30, tzinfo=timezone.utc).timestamp()


class Notifier:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.fail: Exception | None = None
        self.enabled = True

    def send(self, text, html_mode=True, chats=None):
        if self.fail:
            raise self.fail
        self.sent.append(f"[hub] {text}")


def _host(tmp: Path, classes: dict, t: list[float], notifier=None, hub=None) -> PluginHost:
    return PluginHost(tmp / "plugins", hub, notifier or Notifier(), classes=classes, clock=lambda: t[0])


def _cal(tmp: Path, cfg: dict | None = None, t: list[float] | None = None, feed=None, notifier=None, hub=None):
    t = t if t is not None else [CPI - 3600]
    calls: list[str] = []

    def fetcher(url):
        calls.append(url)
        if isinstance(feed, Exception):
            raise feed
        return FEED if feed is None else feed

    class P(FFCalendar):
        def __init__(self):
            super().__init__(fetcher)

    # testy upozornení: porovnanie s kalendárom stratégie SPRÁVY (sync.py) je vypnuté, má vlastné testy nižšie
    cfg = {"strategy_sync": False, **(cfg or {})}
    (tmp / "plugins" / "ff_calendar").mkdir(parents=True, exist_ok=True)
    (tmp / "plugins" / "ff_calendar" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    host = _host(tmp, {"ff_calendar": P}, t, notifier, hub)
    p = host.get("ff_calendar")
    p.calls = calls
    return host, p, t


# --------------------------------------------------------------------------- #
# host
# --------------------------------------------------------------------------- #

def test_discover_najde_pluginy_v_baliku():
    assert {"ff_calendar", "watchdog"} <= set(discover())


def test_host_zachyti_vynimku_zly_plugin_a_vypnutie(tmp_path: Path):
    t = [1000.0]

    class Pada(HubPlugin):
        n = 0

        def tick(self):
            Pada.n += 1
            raise RuntimeError("bum")

    class Zly(HubPlugin):
        def setup(self, ctx):
            raise ImportError("chýba knižnica")

    host = _host(tmp_path, {"pada": Pada, "zly": Zly}, t)
    assert host.run_once("pada") is False and host.run_once("pada") is False
    st = {p["name"]: p for p in host.status()}
    assert st["pada"]["errors"] == 2 and st["pada"]["error_since"] == 1000.0 and "bum" in st["pada"]["last_error"]
    assert st["zly"]["load_error"].startswith("ImportError") and not st["zly"]["enabled"]
    # vypnutie configom bez reštartu
    (tmp_path / "plugins" / "pada").mkdir(parents=True)
    (tmp_path / "plugins" / "pada" / "config.json").write_text('{"enabled": false}', encoding="utf-8")
    assert host.enabled("pada") is False
    # vlákno: vypnutý plugin sa netickuje, stop ho ukončí
    Pada.n = 0
    host.start()
    host.stop()
    for s in host.slots.values():
        if s.thread:
            s.thread.join(2)
    assert Pada.n == 0


def test_notifier_bez_configu_hodi_chybu_a_s_configom_posle_s_labelom(tmp_path: Path, monkeypatch):
    from tester.hub.plugins import HubNotifier

    monkeypatch.delenv("TRADEBOT_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TRADEBOT_TELEGRAM_CHATS", raising=False)
    sent = []

    class Bot:
        def __init__(self, token):
            self.token = token

        def send(self, chat, text, html=False):
            sent.append((self.token, chat, text, html))

    n = HubNotifier(tmp_path / "telegram.json", bot_factory=Bot)
    assert not n.enabled
    try:
        n.send("x")
        raise AssertionError("bez configu má hodiť chybu")
    except NotifyError:
        pass
    (tmp_path / "telegram.json").write_text(json.dumps({"token": "T", "chats": [7, 8], "label": "hub<1>"}),
                                            encoding="utf-8")
    assert n.enabled
    n.send("<b>a</b>")
    assert sent == [("T", 7, "[hub&lt;1&gt;] <b>a</b>", True), ("T", 8, "[hub&lt;1&gt;] <b>a</b>", True)]


# --------------------------------------------------------------------------- #
# ff_calendar
# --------------------------------------------------------------------------- #

def test_feed_ny_cas_na_utc_tyzden_a_zly_cas_von():
    ev = parse_feed(FEED)
    assert len(ev) == 5 and ev[1]["ts"] == CPI
    assert str(feed_week(ev)) == "2026-10-11"                      # nedeľa týždňa exportu
    assert str(ny_week(CPI)) == "2026-10-11"
    assert str(ny_week(datetime(2026, 10, 18, 5, 0, tzinfo=timezone.utc).timestamp())) == "2026-10-18"
    assert parse_feed({"nie": "zoznam"}) == []


def test_config_predvolene_a_odstupy():
    c = CalendarConfig.from_dict({})
    assert c.impact == ["High"] and c.remind_min == [30.0] and c.tz == "Europe/Bratislava" and c.refresh == "07:00"
    assert remind_offsets(60, 3, 20) == [60.0, 40.0, 20.0]
    assert remind_offsets(10, 5, 5) == [10.0, 5.0, 0.0]          # záporné von
    c = CalendarConfig.from_dict({"lead_min": 45, "count": 2, "every_min": 30, "currencies": "usd, eur",
                                  "impact": "high", "refresh": "25:99"})
    assert c.remind_min == [45.0, 15.0] and c.currencies == ["USD", "EUR"] and c.impact == ["High"]
    assert c.refresh_hm() == (7, 0)
    assert CalendarConfig.from_dict({"remind_min": [5, 60, 15], "lead_min": 1}).remind_min == [60.0, 15.0, 5.0]


def test_jedno_upozornenie_30_min_pred_spolu_za_cas_a_restart_neopakuje(tmp_path: Path):
    host, p, t = _cal(tmp_path)
    n = host.notifier
    assert host.run_once("ff_calendar") and n.sent == []          # hodinu pred: nič
    t[0] = CPI - 30 * 60
    host.run_once("ff_calendar")
    assert len(n.sent) == 1
    text = n.sent[0]
    assert text.startswith("[hub] 🔴 <b>o 30 min</b> · <b>14:30</b>")
    assert "<b>USD</b> CPI m/m · progn. 0.6% · pred. 0.4%" in text and "Core CPI m/m" in text
    assert "Retail Sales" not in text                             # Medium nie
    t[0] += 60
    host.run_once("ff_calendar")
    assert len(n.sent) == 1                                       # neopakuje
    # reštart hubu: stav aj zásoba z disku, nič znova a nič nesťahuje
    host2, p2, _ = _cal(tmp_path, t=t, notifier=n)
    host2.run_once("ff_calendar")
    assert len(n.sent) == 1 and p2.calls == [] and len(p2.events) == 5


def test_viac_upozorneni_oneskorene_po_vypadku_a_po_udalosti_nic(tmp_path: Path):
    host, p, t = _cal(tmp_path, {"lead_min": 60, "count": 3, "every_min": 20}, t=[CPI - 61 * 60])
    n = host.notifier
    host.run_once("ff_calendar")
    t[0] = CPI - 60 * 60
    host.run_once("ff_calendar")
    assert "o 60 min" in n.sent[-1]
    t[0] = CPI - 7 * 60                                           # hub nebežal cez 40 aj 20: jedno oneskorené
    host.run_once("ff_calendar")
    assert len(n.sent) == 2 and "o 7 min" in n.sent[-1]
    assert p.sent[f"{int(CPI)}|USD|CPI m/m"] == [60.0, 40.0, 20.0]
    t[0] = CPI + 10
    host.run_once("ff_calendar")
    assert len(n.sent) == 2


def test_filter_meny_a_den_v_hlavicke(tmp_path: Path):
    gdp = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc).timestamp()
    host, p, t = _cal(tmp_path, {"currencies": ["GBP"], "remind_min": [24 * 60]}, t=[gdp - 24 * 3600])
    host.run_once("ff_calendar")
    assert len(host.notifier.sent) == 1
    text = host.notifier.sent[0]
    assert "<b>GBP</b>" in text and "<b>USD</b>" not in text and "o 24 h" in text and "št 15. 10. 08:00" in text


def test_telegram_dole_skusi_znova(tmp_path: Path):
    n = Notifier()
    n.fail = NotifyError("sendMessage: 502")
    host, p, t = _cal(tmp_path, t=[CPI - 29 * 60], notifier=n)
    host.run_once("ff_calendar")
    assert not (tmp_path / "plugins" / "ff_calendar" / "state.json").exists()
    n.fail = None
    host.run_once("ff_calendar")
    assert len(n.sent) == 1


def test_stiahnutie_raz_denne_a_novy_tyzden_kazdu_hodinu(tmp_path: Path):
    # sobota 17. 10. 10:00 Bratislava: stiahne raz (zásoba prázdna)
    sob = datetime(2026, 10, 17, 8, 0, tzinfo=timezone.utc).timestamp()
    host, p, t = _cal(tmp_path, t=[sob])
    host.run_once("ff_calendar")
    assert len(p.calls) == 1
    t[0] += 6 * 3600
    host.run_once("ff_calendar")
    assert len(p.calls) == 1                                       # do zajtra 07:00 nič
    t[0] = datetime(2026, 10, 18, 5, 1, tzinfo=timezone.utc).timestamp()   # ne 07:01 Bratislava
    host.run_once("ff_calendar")
    assert len(p.calls) == 2                                       # denné; export má ešte minulý týždeň
    t[0] += 1800
    host.run_once("ff_calendar")
    assert len(p.calls) == 2
    t[0] += 1800
    host.run_once("ff_calendar")
    assert len(p.calls) == 3                                       # o hodinu znova, kým nepríde nový týždeň
    novy = [dict(e, date=e["date"].replace("2026-10-1", "2026-10-2")) for e in FEED if e["date"][0] == "2"]
    p.fetcher = lambda url: (p.calls.append(url), novy)[1]
    t[0] += 3600
    host.run_once("ff_calendar")
    assert len(p.calls) == 4 and str(feed_week(p.events)) == "2026-10-18"
    t[0] += 3600
    host.run_once("ff_calendar")
    assert len(p.calls) == 4                                       # už má aktuálny týždeň


def test_vypadok_zdroja_zasoba_problem_a_html_namiesto_json(tmp_path: Path):
    host, p, t = _cal(tmp_path, t=[CPI - 3 * 86400])
    host.run_once("ff_calendar")
    p.fetcher = lambda url: (_ for _ in ()).throw(OSError("dns"))
    t[0] += 86400
    host.run_once("ff_calendar")                                   # zlyhá, zásoba ostáva
    assert len(p.events) == 5 and "dns" in p.last_error and p.status()["problem"] is None
    zlyhal = p.fetched
    t[0] += RETRY_FAIL - 10
    host.run_once("ff_calendar")
    assert p.fetched == zlyhal                                     # neúspech skúsi znova až o 15 min
    t[0] = p.fetched_ok + STALE_AFTER + 1
    host.run_once("ff_calendar")
    assert "nedá stiahnuť" in p.status()["problem"]
    p.fetcher = lambda url: (_ for _ in ()).throw(ValueError("nie je JSON"))
    assert p.refresh(force=True) is False


# --------------------------------------------------------------------------- #
# watchdog
# --------------------------------------------------------------------------- #

def _hub(t: list[float]):
    """Hub, ako ho vidí plugin: bez `_lock` — strážca ide cez `PluginContext.agents()` (audit M-HUB-11)."""
    agents = {"nas": {"last_seen": t[0]}}
    return SimpleNamespace(deploy=SimpleNamespace(active_agents=lambda: ["nas"]), agent_timeout=45.0, agents=agents,
                           agents_snapshot=lambda: {n: dict(a) for n, a in agents.items()})


def test_strazca_hlasi_offline_a_navrat_a_po_restarte_neopakuje(tmp_path: Path):
    t = [10_000.0]
    hub = _hub(t)
    n = Notifier()
    host = _host(tmp_path, {"watchdog": Watchdog}, t, n, hub)
    host.run_once("watchdog")
    assert n.sent == []                                           # hneď po štarte hubu nič
    t[0] += 45 + OFFLINE_GRACE + 1
    host.run_once("watchdog")
    assert len(n.sent) == 1 and n.sent[0].startswith("[hub] 🔴 stroj nas")
    host.run_once("watchdog")
    assert len(n.sent) == 1                                       # neopakuje
    host2 = _host(tmp_path, {"watchdog": Watchdog}, t, n, hub)    # reštart hubu si pamätá, že už hlásil
    host2.get("watchdog").started -= 1000
    hub.agents["nas"]["last_seen"] = t[0]
    host2.run_once("watchdog")
    assert n.sent[-1] == "[hub] 🟢 stroj nas sa znova hlási"


def test_strazca_prevezme_stary_stav(tmp_path: Path):
    t = [10_000.0]
    (tmp_path / "telegram_state.json").write_text(json.dumps({"online": {"nas": False}}), encoding="utf-8")
    host = PluginHost(tmp_path / "plugins", _hub(t), Notifier(), classes={"watchdog": Watchdog}, clock=lambda: t[0])
    assert host.get("watchdog").reported == {"nas": False}


def test_strazca_hlasi_padajuci_visiaci_a_problemovy_plugin(tmp_path: Path):
    t = [10_000.0]
    stav = {"problem": None, "fail": False}

    class Iny(HubPlugin):
        title = "Iný"
        max_tick = 60.0

        def tick(self):
            if stav["fail"]:
                raise RuntimeError("bum")

        def status(self):
            return {"problem": stav["problem"]}

    class Zly(HubPlugin):
        def setup(self, ctx):
            raise SyntaxError("preklep")

    n = Notifier()
    host = _host(tmp_path, {"watchdog": Watchdog, "iny": Iny, "zly": Zly}, t, n, SimpleNamespace(deploy=None))
    host.run_once("watchdog")
    assert n.sent == ["[hub] ⚠️ plugin zly: nenačítal sa: SyntaxError: preklep"]
    stav["fail"] = True
    host.run_once("iny")
    t[0] += PLUGIN_GRACE - 1
    host.run_once("iny")
    host.run_once("watchdog")
    assert len(n.sent) == 1                                       # padá krátko: nič
    t[0] += 2
    host.run_once("iny")
    host.run_once("watchdog")
    assert n.sent[-1].startswith("[hub] ⚠️ plugin Iný: padá 5 min: RuntimeError: bum")
    host.run_once("watchdog")
    assert len(n.sent) == 2
    stav["fail"] = False
    host.run_once("iny")
    host.run_once("watchdog")
    assert n.sent[-1] == "[hub] 🟢 plugin Iný je znova v poriadku"
    stav["problem"] = "kalendár sa nedá stiahnuť"
    host.run_once("watchdog")
    assert n.sent[-1] == "[hub] ⚠️ plugin Iný: kalendár sa nedá stiahnuť"
    stav["problem"] = None
    host.run_once("watchdog")
    assert n.sent[-1].startswith("[hub] 🟢")                       # zmena problému na iný sa nehlási, len návrat
    host.slots["iny"].tick_started = t[0] - 120                   # tick visí dlhšie ako max_tick
    host.run_once("watchdog")
    assert n.sent[-1] == "[hub] ⚠️ plugin Iný: visí 2 min"


# --------------------------------------------------------------------------- #
# ff_calendar → kalendár stratégie SPRÁVY (sync.py)
# --------------------------------------------------------------------------- #

def _ff(title: str, when: str, country: str = "USD", impact: str = "High") -> dict:
    return {"title": title, "country": country, "date": when, "impact": impact, "forecast": "", "previous": ""}


def _deploy_hub(tmp: Path):
    """Hub s `DeployStore` a jedným nasadením stratégie so správami (spravynet) a jedným bez nich (ibsnet)."""
    from tradebot.live.deploy import DeployStore
    from tradebot.live.vault import Vault

    store = DeployStore(tmp / "live.sqlite", config_resolver=lambda s, p: {"_strategy": s, "newsAdd": "2026-01-05 09:00 CPI"}
                        if s == "spravynet" else {"_strategy": s}, vault=Vault(key=b"k" * 32))
    acc = store.upsert_account({"platform": "mt5", "label": "Demo", "login": "1", "server": "S"}, by="t")
    spravy = store.create_deployment({"account": acc["id"], "agent": "pc", "strategy": "spravynet", "symbol": "XAUUSD",
                                      "tf": 1, "profile": "profil_1"}, by="t")
    ine = store.create_deployment({"account": acc["id"], "agent": "pc", "strategy": "ibsnet", "symbol": "NAS100",
                                   "tf": 3, "profile": "p"}, by="t")
    udalosti: list[tuple] = []
    hub = SimpleNamespace(deploy=store, log=lambda ev, **kw: udalosti.append((ev, kw)))
    return hub, store, spravy["id"], ine["id"], udalosti


def test_sync_doplni_chybajucu_a_presunutu_spravu_do_nasadeni(tmp_path: Path):
    """Týždeň 29. 11. – 5. 12. 2026: JOLTS je v kalendári 1. 12., ISM služby 3. 12., NFP 4. 12. Feed má JOLTS o deň
    neskôr (presun), ISM služby o 9:45 namiesto 10:00 (iný čas) a navyše maloobchod 3. 12., ktorý kalendár nemá.
    Rozdiel ide do nasadenia stratégie so správami — ručný záznam ostáva — a NFP, ktoré vo feede chýba, sa len oznámi."""
    from tradebot.strategies.spravy import calendar as cal

    feed = [_ff("JOLTS Job Openings", "2026-12-02T10:00:00-05:00"),
            _ff("ISM Services PMI", "2026-12-03T09:45:00-05:00"),
            _ff("Core Retail Sales m/m", "2026-12-03T08:30:00-05:00", impact="Medium"),
            _ff("Retail Sales m/m", "2026-12-03T08:30:00-05:00"),
            _ff("ISM Manufacturing PMI", "2026-12-01T10:00:00-05:00"),
            _ff("Unemployment Claims", "2026-12-03T08:30:00-05:00", impact="Medium"),
            _ff("CPI m/m", "2026-12-02T03:00:00-05:00"),                      # mimo rozumných hodín — ignoruje sa
            _ff("GDP m/m", "2026-12-03T02:00:00-05:00", country="GBP")]
    week = feed_week(parse_feed(feed))
    assert str(week) == "2026-11-29"
    diff = cal.week_diff(parse_feed(feed), week)
    assert cal.fmt_add(diff["add"]) == "2026-12-02 10:00 JOLTS; 2026-12-03 08:30 RETAIL; 2026-12-03 09:45 ISM_S"
    assert cal.fmt_skip(diff["skip"]) == "2026-12-01 JOLTS; 2026-12-03 ISM_S"
    assert cal.fmt_skip(diff["missing"]) == "2026-12-04 NFP"                  # vo feede nie je — len oznámiť
    assert cal.fmt_skip(diff["record"]) == "2026-12-02 JOLTS; 2026-12-03 RETAIL"   # bežný čas typu → do repozitára
    assert cal.fmt_skip(diff["unrecord"]) == "2026-12-01 JOLTS"

    hub, store, spravy, ine, udalosti = _deploy_hub(tmp_path)
    n = Notifier()
    t = [datetime(2026, 11, 30, 6, 0, tzinfo=timezone.utc).timestamp()]
    host, p, _ = _cal(tmp_path, {"strategy_sync": True}, t=t, feed=feed, notifier=n, hub=hub)
    host.run_once("ff_calendar")
    cfg = store.deployment(spravy)["config"]
    assert cfg["newsAdd"] == "2026-01-05 09:00 CPI; 2026-12-02 10:00 JOLTS; 2026-12-03 08:30 RETAIL; 2026-12-03 09:45 ISM_S"
    assert cfg["newsSkip"] == "2026-12-01 JOLTS; 2026-12-03 ISM_S"
    assert "newsAdd" not in store.deployment(ine)["config"]                   # stratégia bez správ sa nemení
    kal = [x for x in n.sent if "Kalendár SPRÁVY" in x]
    assert len(kal) == 1 and "2026-12-04 NFP" in kal[0] and spravy in kal[0]
    assert [e for e, _ in udalosti] == ["plugin_calendar_sync"]
    stav = p.status()["sync"]
    assert stav["deployments"] == [spravy] and stav["pending_repo"] == 3 and not stav["error"]

    # ďalšie stiahnutie bez zmeny: nič sa nezapíše ani neoznámi znova
    rev = store.identity()["rev"]
    t[0] += 26 * 3600
    host.run_once("ff_calendar")
    assert store.identity()["rev"] == rev and len([x for x in n.sent if "Kalendár SPRÁVY" in x]) == 1

    # feed sa v týždni opravil (JOLTS predsa 1. 12.): spravovaný záznam zmizne, ručný ostáva
    feed[0] = _ff("JOLTS Job Openings", "2026-12-01T10:00:00-05:00")
    t[0] += 26 * 3600
    host.run_once("ff_calendar")
    cfg = store.deployment(spravy)["config"]
    assert cfg["newsAdd"] == "2026-01-05 09:00 CPI; 2026-12-03 08:30 RETAIL; 2026-12-03 09:45 ISM_S"
    assert cfg["newsSkip"] == "2026-12-03 ISM_S"


def test_sync_pokazeny_feed_nic_nezmeni_a_vypnuty_nic_nerobi(tmp_path: Path):
    hub, store, spravy, _ine, _ud = _deploy_hub(tmp_path)
    dni = [f"2026-12-{d:02d}" for d in (1, 2, 3, 4)]
    feed = [_ff(nazov, f"{den}T{h:02d}:15:00-05:00") for den in dni
            for h, nazov in ((9, "CPI m/m"), (10, "PPI m/m"), (11, "JOLTS Job Openings"), (12, "Retail Sales m/m"))]
    t = [datetime(2026, 11, 30, 6, 0, tzinfo=timezone.utc).timestamp()]
    host, p, _ = _cal(tmp_path, {"strategy_sync": True}, t=t, feed=feed, hub=hub)
    host.run_once("ff_calendar")
    assert "vyzerá pokazený" in p.status()["sync"]["error"]
    assert store.deployment(spravy)["config"]["newsAdd"] == "2026-01-05 09:00 CPI"

    hub2, store2, spravy2, _i, _u = _deploy_hub(tmp_path / "b")
    host2, p2, _ = _cal(tmp_path / "b", None, t=t, feed=[_ff("JOLTS Job Openings", "2026-12-02T10:00:00-05:00")], hub=hub2)
    host2.run_once("ff_calendar")                                             # `_cal` má sync predvolene vypnutý
    assert store2.deployment(spravy2)["config"]["newsAdd"] == "2026-01-05 09:00 CPI" and p2.status()["sync"]["error"] == ""


def test_sync_pushne_potvrdene_terminy_do_repozitara_raz_za_mesiac(tmp_path: Path, monkeypatch):
    """Termíny v bežnom čase typu idú do `calendar.json` a `SpravyCalendar.cs` vo vlastnom klone — najviac raz za mesiac."""
    import sys
    import types

    from tradebot.strategies.spravy import calendar as cal

    pushe: list[dict] = []

    def push_files(repo, remote, branch, src_root, rels, message, author, *, sub, log=None, ssh_key=None):
        pushe.append({"remote": remote, "branch": branch, "sub": sub, "rels": rels, "message": message,
                      "json": json.loads((Path(src_root) / rels[0]).read_text(encoding="utf-8")),
                      "cs": (Path(src_root) / rels[1]).read_text(encoding="utf-8"), "ssh_key": ssh_key})
        return "abc1234567890"

    monkeypatch.setitem(sys.modules, "tester.hub.plugins.livedata", types.SimpleNamespace(gitpush=types.SimpleNamespace(push_files=push_files)))
    hub, _store, _spravy, _ine, udalosti = _deploy_hub(tmp_path)
    feed = [_ff("JOLTS Job Openings", "2026-12-02T10:00:00-05:00"), _ff("Retail Sales m/m", "2026-12-03T08:30:00-05:00"),
            _ff("ISM Services PMI", "2026-12-03T09:45:00-05:00")]
    t = [datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc).timestamp()]
    cfg = {"strategy_sync": True, "push": {"remote": "git@example:x/y.git", "ssh_key": "kluc", "branch": "main"}}
    host, p, _ = _cal(tmp_path, cfg, t=t, feed=feed, hub=hub)
    host.run_once("ff_calendar")
    assert len(pushe) == 1 and pushe[0]["sub"] == "tradebot/strategies/spravy"
    assert pushe[0]["rels"] == ["calendar.json", "ports/csharp/SpravyCalendar.cs"] and pushe[0]["ssh_key"].name == "kluc"
    novy = pushe[0]["json"]
    assert "2026-12-02" in novy["events"]["JOLTS"]["dates"] and "2026-12-01" not in novy["events"]["JOLTS"]["dates"]
    assert "2026-12-03" in novy["events"]["RETAIL"]["dates"]
    assert novy["events"]["ISM_S"] == cal.load()["events"]["ISM_S"]            # iný čas ostáva len v newsAdd / newsSkip
    assert novy["coverage"]["to"]["JOLTS"] == "2026-12-02" and novy["events"]["JOLTS"]["dates"] == sorted(novy["events"]["JOLTS"]["dates"])
    assert pushe[0]["cs"] == cal.csharp_source(novy) and 'new Ev(2026, 12, 2, 10, 0, "JOLTS")' in pushe[0]["cs"]
    assert "JOLTS 2026-12-02" in pushe[0]["message"] and ("plugin_calendar_push", {"plugin": "ff_calendar", "commit": "abc1234567", "changes": 3}) in udalosti
    assert p.status()["sync"]["commit"] == "abc1234567890"

    # ten istý mesiac znova: nepushuje sa (ani keby pribudlo), ďalší mesiac áno
    t[0] += 26 * 3600
    host.run_once("ff_calendar")
    assert len(pushe) == 1
    t[0] = datetime(2027, 1, 2, 12, 0, tzinfo=timezone.utc).timestamp()
    host.run_once("ff_calendar")
    assert len(pushe) == 2


def test_strazca_hlasi_stroj_ktory_dlho_neposiela_telemetriu(tmp_path: Path):
    """Zvyšok auditu M-HUB-6: stroj je online, ale spool sa mu nedarí poslať — vek chyby stráži hub."""
    t = [10_000.0]
    hub = _hub(t)
    hub.agents["nas"].update(online=True, live={"ship": {"last_error": "hub 503: <dole>", "last_ok": 1.0}})
    n = Notifier()
    host = _host(tmp_path, {"watchdog": Watchdog}, t, n, hub)

    def kolo(posun: float) -> None:
        t[0] += posun
        hub.agents["nas"]["last_seen"] = t[0]
        host.run_once("watchdog")

    kolo(0)
    kolo(SHIP_GRACE - 1)
    assert n.sent == []                                           # krátky výpadok hubu nespamuje
    kolo(2)
    assert len(n.sent) == 1 and "stroj nas už 10 min neposiela telemetriu" in n.sent[0] and "hub 503: &lt;dole&gt;" in n.sent[0]
    kolo(60)
    assert len(n.sent) == 1 and host.get("watchdog").status()["ship_bad"] == ["nas"]
    host2 = _host(tmp_path, {"watchdog": Watchdog}, t, n, hub)    # reštart hubu to isté neohlási znova
    host2.run_once("watchdog")
    assert len(n.sent) == 1
    hub.agents["nas"]["live"]["ship"]["last_error"] = None
    host2.run_once("watchdog")
    assert n.sent[-1] == "[hub] 🟢 stroj nas znova posiela telemetriu" and host2.get("watchdog").status()["ship_bad"] == []
    # offline stroj: posledný známy `ship` je starý — to hlási strážca strojov, nie tento
    hub.agents["nas"].update(online=False, live={"ship": {"last_error": "stará chyba"}})
    assert host2.get("watchdog").ship_messages(t[0]) == ([], False)
    assert host2.get("watchdog").ship_messages(t[0] + SHIP_GRACE + 1) == ([], False)


def test_kontext_pluginu_da_kopiu_agentov_bez_zamku_hubu(tmp_path: Path):
    """Audit M-HUB-11: plugin sa k agentom dostane cez `PluginContext.agents()`, nie cez `hub._lock` a `hub.agents`."""
    from tester.hub.plugins.base import PluginContext
    from tester.hub.state import HubState

    state = HubState(tmp_path / "hub", version="x")
    state.register("nas", instance="i", cores=2, slots=2, accept=False)
    ctx = PluginContext("x", tmp_path / "plugins", state, None)
    kopia = ctx.agents()
    assert kopia["nas"]["online"] is True and kopia["nas"]["last_seen"] > 0
    kopia["nas"]["online"] = "zmenené"
    kopia.pop("nas")
    assert state.agents["nas"]["online"] is True and "nas" in ctx.agents()
    assert PluginContext("x", tmp_path / "plugins", SimpleNamespace(), None).agents() == {}   # hub bez snímky
