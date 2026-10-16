"""Telegram (docs/LIVE.md, „Telegram“) bez siete: formát správ zo spoolu (vstup, výstup s P&L, štart,
režim, note), `LiveNotifier` (prvý štart preskočí históriu, výpadok Telegramu = kurzor stojí a nič sa
nezdvojí, beh v Testeri sa nehlási), príkazy (povolené chaty/admini, `/pause` cez control súbor
a prekrytie, `/flatten` len s potvrdením, 409), prekrytie v agentovi, prevzatie na hube
(`DeployStore.apply_overrides`) a strážca strojov na hube."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from tester.hub.agent import HubAgent
from tester.hub.telegram_watch import OFFLINE_GRACE, HubTelegramWatch
from tradebot.live.deploy import DeployStore
from tradebot.live.spool import SpoolReader
from tradebot.live.telegram import (ControlFiles, LiveNotifier, TelegramBot, TelegramCommands, TelegramConfig,
                                    TelegramConflict, TelegramError, TelegramState, format_event, ikey, load_config)
from tradebot.live.vault import Vault

INST = "mt5_1514925336-FTMO-Demo_US100.cash_3m_vwaporbnet"


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str, list | None]] = []
        self.fail: Exception | None = None
        self.ups: list[dict] = []
        self.answered: list[str] = []
        self.edited: list[tuple[int, int, str]] = []

    def send(self, chat, text, buttons=None, html=False, keyboard=None):
        if self.fail:
            raise self.fail
        self.sent.append((chat, text, buttons or keyboard))

    def updates(self, offset, timeout=3):
        if isinstance(self.fail, TelegramConflict):
            raise self.fail
        out, self.ups = [u for u in self.ups if u["update_id"] >= offset], []
        return out

    def answer(self, cid, text=""):
        self.answered.append(cid)

    def edit(self, chat, mid, text, buttons=None, html=False):
        self.edited.append((chat, mid, text, buttons))


CFG = TelegramConfig(token="t", chats=[7], admins=[42])


def hello(seq=1, session="s1", tester=False):
    return {"seq": seq, "t": 1, "k": "hello", "schema": 1, "platform": "mt5", "account": "1514925336-FTMO-Demo",
            "symbol": "US100.cash", "tf": 3, "strategy": "vwaporbnet", "profile": "P1", "session": session,
            "tester": tester, "instrument": {"point_value": 1.0}}


def write(root: Path, events: list[dict], session="s1", inst=INST) -> Path:
    d = root / inst
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"20261016-064928_{session}.jsonl"
    with open(p, "a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")
    return p


def entry(seq, ready=True):
    return {"seq": seq, "t": 2, "k": "order", "bt": 1, "ready": ready, "a": "entry", "id": "orb:1", "dir": -1,
            "ot": "Market", "p": {"dir": -1, "e": 29152.03, "sl": 29851.44, "tp": 28802.33, "q": 0.14}}


def fill(seq, side, price, qty=0.14, exit_=""):
    return {"seq": seq, "t": 3, "k": "fill", "ft": 3, "id": "orb:1", "side": side, "exit": exit_, "price": price,
            "qty": qty, "ready": True}


def test_format_vstup_vystup_s_pnl_a_filtre():
    ctx = {"platform": "mt5", "account": "A", "symbol": "US100.cash", "tf": 3, "strategy": "vwaporbnet",
           "point_value": 1.0}
    assert format_event(ctx, entry(2), CFG) is None                                     # signály vypnuté
    assert "📍 signál SHORT" in format_event(dict(ctx), entry(2), TelegramConfig(token="t", signals=True))
    vstup = format_event(ctx, fill(3, "in", 29152.0), CFG)
    assert vstup.startswith("🟢 VSTUP SHORT × 0.14 @ 29152") and "SL 29851.44" in vstup and "MT5 A" in vstup
    vystup = format_event(ctx, fill(4, "out", 28802.0, exit_="sltp"), CFG)
    assert vystup.startswith("✅ VÝSTUP sltp SHORT") and "+350.00 b" in vystup and "+49.00 $" in vystup
    assert ctx["open"] == {}
    # note podľa úrovne, control, pending sa nehlási
    assert format_event(ctx, {"k": "note", "text": "x", "level": "info"}, CFG) is None
    assert format_event(ctx, {"k": "note", "text": "rejected", "level": "warn"}, CFG).startswith("⚠")
    assert format_event(ctx, {"k": "control", "mode": "paused", "source": "control"}, CFG).startswith("⏸")
    assert format_event(ctx, {"k": "control", "mode": "paused", "source": "pending"}, CFG) is None
    assert format_event(ctx, {"k": "bar"}, CFG) is None


def test_notifier_preskoci_historiu_posiela_nove_a_po_vypadku_nezdvoji(tmp_path: Path):
    root = tmp_path / "spool"
    write(root, [hello(), entry(2), fill(3, "in", 29152.0)])     # história pred štartom
    bot = FakeBot()
    state = TelegramState(tmp_path / "tg.json")
    n = LiveNotifier(SpoolReader([root], tmp_path / "cur.json"), bot, CFG, state)
    assert n.pump()["skipped_history"] and bot.sent == []
    write(root, [fill(4, "out", 28802.0, exit_="sltp")])
    assert n.pump()["sent"] == 1
    assert bot.sent[0][0] == 7 and "+350.00 b" in bot.sent[0][1]          # P&L z otvorenej pozície z histórie

    # Telegram dole: kurzor stojí, po návrate príde raz
    write(root, [{"seq": 5, "t": 5, "k": "note", "text": "TradeBot: vstup odmietnutý", "level": "warn"},
                 {"seq": 6, "t": 6, "k": "control", "mode": "paused", "source": "control"}])
    bot.fail = TelegramError("sendMessage: 502")
    assert n.pump()["error"]
    bot.fail = None
    assert n.pump()["sent"] == 2 and len(bot.sent) == 2                   # dve udalosti zlúčené do jednej správy
    assert "odmietnutý" in bot.sent[1][1] and "⏸" in bot.sent[1][1]
    assert n.pump()["sent"] == 0

    # nový reconciler/proces nad tým istým stavom nič neopakuje
    n2 = LiveNotifier(SpoolReader([root], tmp_path / "cur.json"), bot, CFG, TelegramState(tmp_path / "tg.json"))
    assert n2.pump()["sent"] == 0


def test_notifier_nehlasi_tester_a_rotaciu_dna(tmp_path: Path):
    root = tmp_path / "spool"
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"))
    n.pump()   # prázdna história
    write(root, [hello(session="tt", tester=True), fill(2, "in", 1.0)], session="tt", inst=INST + "x")
    write(root, [hello(), entry(2, ready=False)])
    n.pump()
    assert [t for _, t, _ in bot.sent] == ["▶ US100.cash 3m vwaporbnet · MT5 1514925336-FTMO-Demo beží (profil P1)"]
    # nový súbor tej istej session (zmena UTC dňa) zopakuje hello — bez správy, zámer vstupu ostáva
    p = root / INST / "20261017-000000_s1.jsonl"
    p.write_text(json.dumps(hello(seq=3)) + "\n" + json.dumps(fill(4, "in", 29152.0)) + "\n", encoding="utf-8")
    n.pump()
    assert len(bot.sent) == 2 and bot.sent[1][1].startswith("🟢 VSTUP SHORT")


def test_report_issues_hlasi_zmenu_a_navrat(tmp_path: Path):
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"))
    assert n.report_issues({"d1": ("vwaporbnet US100.cash 3m (ftmo)", "")}) == 0
    assert n.report_issues({"d1": ("vwaporbnet US100.cash 3m (ftmo)", "nenabehla: terminál nebeží")}) == 1
    assert n.report_issues({"d1": ("vwaporbnet US100.cash 3m (ftmo)", "nenabehla: terminál nebeží")}) == 0
    assert n.report_issues({}) == 1 and "je v poriadku" in bot.sent[-1][1]


class FakeControls:
    def __init__(self) -> None:
        self.modes: dict[str, str] = {INST: "enabled", "ninjatrader_DEMO_MNQ_3m_vwaporbnet": "enabled"}

    def instances(self, now=None):
        return [{"instance": i, "symbol": i.split("_")[2], "tf": 3, "strategy": "vwaporbnet",
                 "platform": i.split("_")[0], "account": "A", "last_bar_ms": None, "ended": False, "control": m}
                for i, m in sorted(self.modes.items())]

    def set_mode(self, instance, mode, by):
        self.modes[instance] = mode


def msg(text, user=42, chat=7, uid=1):
    return {"update_id": uid, "message": {"chat": {"id": chat}, "from": {"id": user}, "text": text}}


def cb(data, uid, qid="q", mid=11, user=42):
    return {"update_id": uid, "callback_query": {"id": qid, "from": {"id": user}, "data": data,
                                                 "message": {"message_id": mid, "chat": {"id": 7}}}}


def test_prikazy_gombiky_pause_flatten_povolenia_a_konflikt(tmp_path: Path):
    bot, ctl = FakeBot(), FakeControls()
    state = TelegramState(tmp_path / "s.json")
    zmeny = []
    cmd = TelegramCommands(bot, CFG, state, ctl, clock=lambda: 1000.0, on_change=lambda: zmeny.append(1))
    bot.ups = [msg("/pause 2", user=99, uid=1), msg("/pause 1", chat=8, uid=2), cb("P:*", 3, user=99)]
    assert cmd.poll() == 3 and bot.sent == [] and ctl.modes[INST] == "enabled"     # cudzí používateľ, chat, gombík
    assert state.data["update_offset"] == 4

    # /start = pomoc so stálou klávesnicou; jej gombík „📊 Stav“ = /status s gombíkom na každú stratégiu
    bot.ups = [msg("/start", uid=4), msg("📊 Stav", uid=5)]
    cmd.poll()
    assert bot.sent[0][2][0] == ["📊 Stav", "📋 Ordery"]
    text, rows = bot.sent[1][1], bot.sent[1][2]
    assert "<b>MT5</b>" in text and "<b>NINJATRADER</b>" not in text and "<b>NT8</b>" in text
    assert "1. ▶ <b>US100.cash 3m</b>" in text and "2. ▶ <b>MNQ 3m</b>" in text
    assert rows[0][0]["callback_data"] == f"m:{ikey(INST)}" and rows[-1][1]["callback_data"] == "o"

    # ťuk na stratégiu → ponuka, ťuk na Pauza → control + prekrytie, správa sa prepíše na nový stav
    k = ikey(INST)
    bot.ups = [cb(f"m:{k}", 6), cb(f"P:{k}", 7)]
    cmd.poll()
    assert "Režim: ▶ obchoduje" in bot.edited[0][2] and bot.edited[0][3][0][0]["callback_data"] == f"P:{k}"
    assert ctl.modes[INST] == "paused" and zmeny == [1] and "Režim: ⏸ pauza" in bot.edited[1][2]
    assert state.overrides() == [{"instance": INST, "mode": "paused", "by": "telegram:42", "ts": 1000.0}]

    # flatten: najprv otázka, zmena až po potvrdení; vypršané potvrdenie nič nespraví
    bot.ups = [cb(f"F:{k}", 8)]
    cmd.poll()
    assert ctl.modes[INST] == "paused" and bot.edited[-1][3][0][0]["callback_data"] == f"X:1000:{k}"
    bot.ups = [cb(f"X:1000:{k}", 9)]
    cmd.poll()
    assert ctl.modes[INST] == "flatten" and ctl.modes["ninjatrader_DEMO_MNQ_3m_vwaporbnet"] == "enabled"
    cmd.clock = lambda: 2000.0
    bot.ups = [cb("X:1000:*", 10)]
    cmd.poll()
    assert ctl.modes["ninjatrader_DEMO_MNQ_3m_vwaporbnet"] == "enabled" and "vypršalo" in bot.edited[-1][2]
    # textový /flatten all dá tú istú otázku; gombík zo starej správy (`flatten:<čas>:<id>`) ešte funguje
    bot.ups = [msg("/flatten all", uid=11), cb(f"flatten:2000:{INST}", 12)]
    cmd.poll()
    assert bot.sent[-1][2][0][0]["callback_data"] == "X:2000:*" and ctl.modes[INST] == "flatten"
    # textové príkazy ostávajú
    bot.ups = [msg("/resume US100", uid=13)]
    cmd.poll()
    assert ctl.modes[INST] == "enabled" and "✓ US100.cash 3m vwaporbnet: obchoduje" in bot.sent[-1][1]

    # iný proces už počúva na tom istom bote: príkazy sa vypnú, nič nepadne
    bot.fail = TelegramConflict("getUpdates: 409")
    assert cmd.poll() == 0 and cmd.disabled and cmd.poll() == 0


def test_ordery_pozicie_cakajuce_vstupy_a_nerealizovany_zisk(tmp_path: Path):
    bot, ctl = FakeBot(), FakeControls()
    state = TelegramState(tmp_path / "s.json")
    ctx = {"platform": "mt5", "account": "A", "symbol": "US100.cash", "tf": 3, "strategy": "vwaporbnet",
           "point_value": 1.0}
    for ev in (entry(2), fill(3, "in", 29152.0),
               {"seq": 4, "k": "order", "bt": 1, "ready": True, "a": "modify", "id": "orb:1", "p": {"sl": 29500.0, "tp": None}},
               {"seq": 5, "k": "bar", "bt": 2, "o": 1, "h": 1, "l": 1, "c": 29100.0, "v": 1, "ready": True},
               {**entry(6), "id": "orb:2", "ot": "Limit"}, {**entry(7), "id": "orb:3"},
               {"seq": 8, "k": "order", "bt": 3, "ready": True, "a": "cancel", "id": "orb:3"}):
        format_event(ctx, ev, CFG)
    state.data["ctx"][INST] = ctx
    cmd = TelegramCommands(bot, CFG, state, ctl, clock=lambda: 1000.0)
    text, _ = cmd.orders_view()
    assert "SHORT 0.14 @ 29152 · SL 29500 TP 28802.33 · teraz 29100 (+52.00 b, +7.28 $)" in text
    assert text.count("@ 29152.03") == 1 and "Limit" in text           # orb:2 čaká, orb:3 zrušený, orb:1 vyplnený
    assert "SHORT 0.14" in cmd.status_view()[0] and "čaká 1" in cmd.status_view()[0]
    # nový beh tej istej inštancie (reštart terminálu) si pozíciu u brokera nechá, zámery nie
    n = LiveNotifier(SpoolReader([], tmp_path / "c.json"), bot, CFG, state)
    b = SimpleNamespace(instance=INST, session="s2", path=tmp_path / "x.jsonl", events=[hello(session="s2")])
    n.messages(b)
    assert list(state.data["ctx"][INST]["open"]) == ["orb:1"] and state.data["ctx"][INST]["entries"] == {}


def test_stare_instancie_sa_v_ponuke_neukazuju(tmp_path: Path):
    root = tmp_path / "spool"
    novy = dict(hello(), t=1_000_000_000_000)
    write(root, [novy], inst=INST)
    write(root, [dict(hello(), t=1_000_000_000_000 - 8 * 86400_000)], inst="mt5_stary_US100.cash_1m_ibsnet")
    ctl = ControlFiles(lambda: [root])
    assert [i["instance"] for i in ctl.instances(now=1_000_000_000)] == [INST]
    assert len(ctl.instances(now=1_000_000_000, stale_days=30)) == 2


def test_chyba_rovnaka_az_na_cas_pokusu_sa_neopakuje(tmp_path: Path):
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"))
    d = "vwaporbnet MNQ 3m (demo)"
    assert n.report_issues({"d1": (d, "nenabehla: pripojenie nie je Connected (23:09:44 UTC)")}) == 1
    assert n.report_issues({"d1": (d, "nenabehla: pripojenie nie je Connected (23:10:14 UTC)")}) == 0
    assert "(23:09:44 UTC)" not in bot.sent[0][1]


def test_jedno_kolo_jedna_sprava_za_vsetky_instancie(tmp_path: Path):
    root = tmp_path / "spool"
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"))
    n.pump()
    for k in range(3):
        write(root, [hello(session=f"s{k}"), {"seq": 2, "t": 2, "k": "bye", "reason": "terminated"}],
              session=f"s{k}", inst=f"{INST}{k}")
    assert n.pump()["sent"] == 6 and len(bot.sent) == 1


def test_bot_drzi_odstup_a_caka_na_429():
    volania, spanky = [], []
    odpovede = [{"ok": False, "error_code": 429, "parameters": {"retry_after": 3}}, {"ok": True, "result": {}},
                {"ok": True, "result": {}}]
    t = [0.0]
    bot = TelegramBot("x", opener=lambda m, p, to: (volania.append(m), odpovede.pop(0))[1], clock=lambda: t[0],
                      sleep=lambda s: (spanky.append(s), t.__setitem__(0, t[0] + s)))
    bot.send(7, "a")
    bot.send(7, "b")
    assert volania == ["sendMessage"] * 3 and spanky[0] == 3 and spanky[1] > 0.9


def test_load_config_env_a_chyby(tmp_path: Path, monkeypatch):
    p = tmp_path / "telegram.json"
    assert load_config(p) is None
    p.write_text(json.dumps({"token": "abc", "chats": [1, "2"], "admins": "3", "signals": True}), encoding="utf-8")
    cfg = load_config(p)
    assert cfg.chats == [1, 2] and cfg.admins == [3] and cfg.signals and cfg.notes == "warn"
    p.write_text(json.dumps({"token": "abc", "chats": 5, "admins": 5}), encoding="utf-8")   # PowerShell 5.1
    assert load_config(p).chats == [5] and load_config(p).admins == [5]
    monkeypatch.setenv("TRADEBOT_TELEGRAM_CHATS", "9,10")
    assert load_config(p).chats == [9, 10]


def test_prekrytie_v_agentovi_drzi_kym_ho_hub_neprevezme(tmp_path: Path):
    state = TelegramState(tmp_path / "s.json")
    state.set_override(INST, "paused", "telegram:42", 500.0)
    fake = SimpleNamespace(_telegram=SimpleNamespace(state=state))
    dep = {"id": "d1", "instance": INST, "mode": "enabled", "active": True, "updated": 400.0}
    out = HubAgent._with_overrides(fake, {"deployments": [dep]})
    assert out["deployments"][0]["mode"] == "paused" and dep["mode"] == "enabled" and state.overrides()
    # hub prevzal (rovnaký režim) → prekrytie preč
    HubAgent._with_overrides(fake, {"deployments": [{**dep, "mode": "paused", "updated": 600.0}]})
    assert state.overrides() == []
    # hub zmenil nasadenie neskôr než Telegram → hub vyhráva
    state.set_override(INST, "paused", "telegram:42", 500.0)
    out = HubAgent._with_overrides(fake, {"deployments": [{**dep, "updated": 700.0}]})
    assert out["deployments"][0]["mode"] == "enabled" and state.overrides() == []


def _store(tmp_path: Path, t: list[float]) -> DeployStore:
    return DeployStore(tmp_path / "live.sqlite", clock=lambda: t[0], vault=Vault(key=b"k" * 32),
                       config_resolver=lambda s, p: {"profile": p}, strategy_check=lambda k: k)


def test_hub_prevezme_prepnutie_len_ked_nie_je_novsie(tmp_path: Path):
    t = [1000.0]
    store = _store(tmp_path, t)
    a = store.upsert_account({"platform": "mt5", "label": "FTMO", "login": "1514925336", "server": "FTMO-Demo"}, by="r")
    d = store.create_deployment({"account": a["id"], "agent": "nas", "strategy": "vwaporbnet", "symbol": "US100.cash",
                                 "tf": 3, "profile": "p1", "mode": "enabled"}, by="r")
    inst = d["instance"]
    assert store.active_agents() == ["nas"]
    t[0] = 1100.0
    assert store.apply_overrides("iny", [{"instance": inst, "mode": "paused", "ts": 1050.0}]) == 0   # cudzí stroj
    assert store.apply_overrides("nas", [{"instance": inst, "mode": "paused", "ts": 900.0}]) == 0    # hub je novší
    assert store.apply_overrides("nas", [{"instance": inst, "mode": "paused", "ts": 1050.0, "by": "telegram:42"}]) == 1
    assert store.deployment(d["id"])["mode"] == "paused" and store.audit()[0]["by"] == "telegram:42@nas"
    assert store.apply_overrides("nas", [{"instance": inst, "mode": "paused", "ts": 1050.0}]) == 0   # už má


def test_strazca_hubu_hlasi_offline_a_navrat(tmp_path: Path):
    t = [10_000.0]
    deploy = SimpleNamespace(active_agents=lambda: ["nas"])
    hub = SimpleNamespace(deploy=deploy, agent_timeout=45.0, agents={"nas": {"last_seen": 10_000.0}},
                          _lock=__import__("threading").RLock())
    bot = FakeBot()
    w = HubTelegramWatch(hub, TelegramConfig(token="t", chats=[7], label="hub"), tmp_path / "w.json", bot=bot,
                         clock=lambda: t[0])
    assert w.check() == []                     # hneď po štarte hubu nič
    t[0] += 45 + OFFLINE_GRACE + 1
    assert len(w.check()) == 1 and bot.sent[0][1].startswith("[hub] 🔴 stroj nas")
    assert w.check() == []                     # neopakuje
    # nový strážca (reštart hubu) si pamätá, že už hlásil
    w2 = HubTelegramWatch(hub, w.cfg, tmp_path / "w.json", bot=bot, clock=lambda: t[0] + 1000)
    w2.started -= 1000
    hub.agents["nas"]["last_seen"] = t[0] + 1000
    assert w2.check() == ["🟢 stroj nas sa znova hlási"] and bot.sent[-1][1] == "[hub] 🟢 stroj nas sa znova hlási"
