"""Pluginy hubu (`tester.hub.plugins`, docs/HUB.md, „Pluginy“): host, kalendár ForexFactory, strážca."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from tester.hub.plugins import HubPlugin, NotifyError, PluginHost, discover
from tester.hub.plugins.ff_calendar.alerts import CalendarConfig, remind_offsets
from tester.hub.plugins.ff_calendar.feed import feed_week, ny_week, parse_feed
from tester.hub.plugins.ff_calendar.plugin import RETRY_FAIL, STALE_AFTER, FFCalendar
from tester.hub.plugins.watchdog.plugin import OFFLINE_GRACE, PLUGIN_GRACE, Watchdog

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


def _cal(tmp: Path, cfg: dict | None = None, t: list[float] | None = None, feed=None, notifier=None):
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

    if cfg is not None:
        (tmp / "plugins" / "ff_calendar").mkdir(parents=True, exist_ok=True)
        (tmp / "plugins" / "ff_calendar" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    host = _host(tmp, {"ff_calendar": P}, t, notifier)
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
    return SimpleNamespace(deploy=SimpleNamespace(active_agents=lambda: ["nas"]), agent_timeout=45.0,
                           agents={"nas": {"last_seen": t[0]}}, _lock=threading.RLock())


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
