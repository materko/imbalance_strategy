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
from tradebot.live.deploy import DeployStore
from tradebot.live.spool import SpoolReader
from tradebot.live.telegram import (ControlFiles, LiveNotifier, TelegramBot, TelegramCommands, TelegramConfig,
                                    TelegramConflict, TelegramError, TelegramState, akey, format_event, ikey,
                                    load_config)
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
        if getattr(self, "edit_fail", None):
            raise self.edit_fail
        self.edited.append((chat, mid, text, buttons))

    def pin(self, chat, mid):
        self.pinned = getattr(self, "pinned", set()) | {mid}

    def unpin(self, chat, mid):
        self.pinned = getattr(self, "pinned", set()) - {mid}


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
    assert "📍 <b>Signál SHORT</b>" in format_event(dict(ctx), entry(2), TelegramConfig(token="t", signals=True))
    vstup = format_event(ctx, fill(3, "in", 29152.0), CFG)
    assert vstup == "🟢 <b>VSTUP SHORT</b> × 0.14 @ 29152\n<b>US100</b> vwaporbnet · MT5 · A · SL 29851.44 · TP 28802.33"
    vystup = format_event(ctx, fill(4, "out", 28802.0, exit_="sltp"), CFG)
    assert vystup == "✅ <b>VÝSTUP SHORT</b> × 0.14 @ 28802 · <b>+49.00 $</b> (+350.00 b)\n<b>US100</b> vwaporbnet · MT5 · A (sltp)"
    assert ctx["open"] == {} and "US100.cash" not in vystup        # z bodky by Telegram urobil odkaz
    # note podľa úrovne (escapovaná), štart/koniec/režim tu správu nedávajú (idú súhrnom)
    assert format_event(ctx, {"k": "note", "text": "x", "level": "info"}, CFG) is None
    assert format_event(ctx, {"k": "note", "text": "a<b", "level": "warn"}, CFG) == "⚠️ <b>US100</b> vwaporbnet · MT5 · A\na&lt;b"
    for ev in ({"k": "control", "mode": "paused"}, {"k": "hello"}, {"k": "bye"}, {"k": "bar"}):
        assert format_event(ctx, ev, CFG) is None


def test_notifier_preskoci_historiu_posiela_nove_a_po_vypadku_nezdvoji(tmp_path: Path):
    root = tmp_path / "spool"
    write(root, [hello(), entry(2), fill(3, "in", 29152.0)])     # história pred štartom
    bot = FakeBot()
    state = TelegramState(tmp_path / "tg.json")
    n = LiveNotifier(SpoolReader([root], tmp_path / "cur.json"), bot, CFG, state)
    assert n.pump()["skipped_history"] and bot.sent == [] and state.data["life"] == {}
    write(root, [fill(4, "out", 28802.0, exit_="sltp")])
    assert n.pump()["sent"] == 1
    assert bot.sent[0][0] == 7 and "+49.00 $" in bot.sent[0][1]           # P&L z otvorenej pozície z histórie

    # Telegram dole: kurzor stojí, po návrate príde raz
    write(root, [{"seq": 5, "t": 5, "k": "note", "text": "TradeBot: vstup odmietnutý", "level": "warn"},
                 {"seq": 6, "t": 6, "k": "note", "text": "druhá", "level": "error"}])
    bot.fail = TelegramError("sendMessage: 502")
    assert n.pump()["error"]
    bot.fail = None
    assert n.pump()["sent"] == 2 and len(bot.sent) == 2                   # dve udalosti v jednej správe
    assert "odmietnutý" in bot.sent[1][1] and "\n\n🛑" in bot.sent[1][1]
    assert n.pump()["sent"] == 0

    # nový proces nad tým istým stavom nič neopakuje
    n2 = LiveNotifier(SpoolReader([root], tmp_path / "cur.json"), bot, CFG, TelegramState(tmp_path / "tg.json"))
    assert n2.pump()["sent"] == 0


def test_chyba_telegramu_nezdvoji_vstup_a_otravena_sprava_nezastavi_ostatne(tmp_path: Path):
    """Audit N-LIVE-17: pri chybe sa kontext (otvorené vstupy) uložil, `seq` nie — po opakovaní bol vstup
    započítaný dvakrát; 400/403 jedného chatu zastavilo všetky."""
    root = tmp_path / "spool"
    write(root, [hello(), entry(2)])
    bot = FakeBot()
    state = TelegramState(tmp_path / "tg.json")
    n = LiveNotifier(SpoolReader([root], tmp_path / "cur.json"), bot, CFG, state)
    n.pump()                                                               # história
    write(root, [fill(3, "in", 29152.0)])
    bot.fail = TelegramError("sendMessage: 502", code=502)
    assert n.pump()["error"]
    bot.fail = None
    assert n.pump()["sent"] == 1
    otvorene = next(c for c in state.data["ctx"].values() if "open" in c)["open"]
    assert [round(o["qty"], 2) for o in otvorene.values()] == [0.14]       # nie 0.28

    class Otraveny(FakeBot):
        def send(self, chat, text, buttons=None, html=False, keyboard=None):
            if chat == 7:
                raise TelegramError("sendMessage: 403 Forbidden: bot was kicked", code=403)
            super().send(chat, text, buttons, html, keyboard)

    bot2 = Otraveny()
    n2 = LiveNotifier(SpoolReader([root], tmp_path / "cur.json"), bot2,
                      TelegramConfig(token="t", chats=[7, 8], admins=[42]), state)
    write(root, [fill(4, "out", 28802.0, exit_="sltp")])
    out = n2.pump()
    assert out["sent"] == 1 and [c for c, *_ in bot2.sent] == [8] and "403" in (n2.last_error or "")
    assert n2.pump()["sent"] == 0                                          # kurzor sa posunul, nezasekne sa


def test_restart_troch_strategii_je_jeden_suhrn_po_utichnuti(tmp_path: Path):
    root = tmp_path / "spool"
    t = [1000.0]
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"),
                     clock=lambda: t[0])
    for k in range(3):   # bežiace pred zapnutím Telegramu
        write(root, [hello(session=f"a{k}"), {"seq": 2, "t": 2, "k": "control", "mode": "enabled", "source": "control"}],
              session=f"a{k}", inst=f"{INST}{k}")
    n.pump()
    for k in range(3):   # reštart terminálu: bye, nový beh, EA znova potvrdí enabled
        write(root, [{"seq": 3, "t": 3, "k": "bye", "reason": "deinit"}], session=f"a{k}", inst=f"{INST}{k}")
        write(root, [hello(session=f"b{k}"), {"seq": 2, "t": 2, "k": "control", "mode": "enabled", "source": "control"}],
              session=f"b{k}", inst=f"{INST}{k}")
        n.pump()
        t[0] += 10
    assert bot.sent == []                                   # ešte sa zbiera
    t[0] += 30
    n.pump()
    assert [x[1] for x in bot.sent] == ["🔄 <b>Reštart</b> · MT5 · <b>US100</b>: vwaporbnet, vwaporbnet, vwaporbnet"]
    # pauza jednej = jeden riadok; ten istý režim znova nie
    write(root, [{"seq": 3, "t": 3, "k": "control", "mode": "paused", "source": "control"},
                 {"seq": 4, "t": 4, "k": "control", "mode": "paused", "source": "control"}], session="b0", inst=f"{INST}0")
    n.pump()
    t[0] += 31
    n.pump()
    assert bot.sent[-1][1] == "⏸ <b>Pauza</b> · MT5 · <b>US100</b>: vwaporbnet" and len(bot.sent) == 2


def test_restart_s_dlhou_predhistoriou_je_jeden_suhrn(tmp_path: Path):
    """Po reštarte každá inštancia prehrá tisíce barov; po 500 udalostiach na kolo dobiehali hello jednotlivých
    inštancií minúty po sebe a súhrn reštartu chodil po kúskoch. Jedno kolo číta, kým je čo."""
    root = tmp_path / "spool"
    t = [1000.0]
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"),
                     clock=lambda: t[0])
    for k in range(3):
        write(root, [hello(session=f"a{k}")], session=f"a{k}", inst=f"{INST}{k}")
    n.pump()
    for k in range(3):
        write(root, [{"seq": 2, "t": 2, "k": "bye", "reason": "deinit"}], session=f"a{k}", inst=f"{INST}{k}")
        historia = [{"seq": s, "t": 3, "k": "bar", "bt": 1_790_000_000_000 + s * 180_000, "o": 1.0, "h": 2.0,
                     "l": 0.5, "c": 1.5, "v": 1, "ready": False} for s in range(2, 3002)]
        write(root, [hello(session=f"b{k}"), *historia], session=f"b{k}", inst=f"{INST}{k}")
    n.pump()                                                # jedno kolo prečíta všetkých 9000+ udalostí
    assert n.reader.read(1) == []
    t[0] += 31
    n.pump()
    assert [x[1] for x in bot.sent] == ["🔄 <b>Reštart</b> · MT5 · <b>US100</b>: vwaporbnet, vwaporbnet, vwaporbnet"]


def test_restart_a_stop_nesu_kto_ich_urobil(tmp_path: Path):
    """Zmena nasadenia (`by`) alebo nový kód na stroj (`requested_by`) z hubu → súhrn štartu a stopu ukáže kto."""
    root = tmp_path / "spool"
    t = [1000.0]
    bot = FakeBot()
    state = TelegramState(tmp_path / "s.json")
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), bot, CFG, state, clock=lambda: t[0])
    deps = [{"id": f"d{k}", "instance": f"{INST}{k}", "active": True, "updated": 1.0, "by": "stary"} for k in range(3)]
    state.note_desired({"deployments": deps}, t[0])                    # základ: staré zmeny nikomu
    assert state.actor(f"{INST}0", t[0]) == ""
    for k in range(3):
        write(root, [hello(session=f"a{k}")], session=f"a{k}", inst=f"{INST}{k}")
    n.pump()
    deps[0] = {**deps[0], "updated": 2.0, "by": "rasto"}
    state.note_desired({"deployments": deps}, t[0])
    state.note_desired({"deployments": deps, "code_target": {"version": "abc", "ts": "x", "requested_by": "martin"}}, t[0])
    deps[0] = {**deps[0], "updated": 3.0, "by": "rasto"}               # rasto znova (po kóde), jeho to ostáva
    state.note_desired({"deployments": deps, "code_target": {"version": "abc", "ts": "x", "requested_by": "martin"}}, t[0])
    for k in range(3):
        write(root, [{"seq": 2, "t": 2, "k": "bye", "reason": "deinit"}], session=f"a{k}", inst=f"{INST}{k}")
        write(root, [hello(session=f"b{k}")], session=f"b{k}", inst=f"{INST}{k}")
    write(root, [{"seq": 2, "t": 2, "k": "bye", "reason": "removed"}], session="b0", inst=f"{INST}0")
    n.pump()
    t[0] += 31
    n.pump()
    assert bot.sent[-1][1] == ("🔄 <b>Reštart</b> · MT5 · <b>US100</b>: vwaporbnet (👤 martin), vwaporbnet (👤 martin)\n"
                               "⏹ <b>Zastavené</b> · MT5 · <b>US100</b>: vwaporbnet (removed · 👤 rasto)")
    # po ACTOR_TTL sa už nikomu nepripíše (pád terminálu o hodinu nie je rastov)
    t[0] += 3600
    write(root, [hello(session="c1")], session="c1", inst=f"{INST}1")
    n.pump()
    t[0] += 31
    n.pump()
    assert bot.sent[-1][1] == "▶️ <b>Spustené</b> · MT5 · <b>US100</b>: vwaporbnet"


def test_notifier_nehlasi_tester_a_rotaciu_dna(tmp_path: Path):
    root = tmp_path / "spool"
    t = [1000.0]
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"),
                     clock=lambda: t[0])
    n.pump()   # prázdna história
    write(root, [hello(session="tt", tester=True), fill(2, "in", 1.0)], session="tt", inst=INST + "x")
    write(root, [hello(), entry(2, ready=False)])
    n.pump()
    t[0] += 31
    n.pump()
    assert [x[1] for x in bot.sent] == ["▶️ <b>Spustené</b> · MT5 · <b>US100</b>: vwaporbnet"]
    # nový súbor tej istej session (zmena UTC dňa) zopakuje hello — bez správy, zámer vstupu ostáva
    p = root / INST / "20261017-000000_s1.jsonl"
    p.write_text(json.dumps(hello(seq=3)) + "\n" + json.dumps(fill(4, "in", 29152.0)) + "\n", encoding="utf-8")
    n.pump()
    t[0] += 31
    n.pump()
    assert len(bot.sent) == 2 and bot.sent[1][1].startswith("🟢 <b>VSTUP SHORT</b>")


def test_report_issues_hlasi_zmenu_a_navrat_zoskupene(tmp_path: Path):
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"))
    chyba = ("nenabehla: pripojenie 'Simulation' nie je Connected - skusim znova neskor — pripojenie 'Simulation' "
             "v Core.Globals.ConnectOptions nie je (su: Simulated Data Feed) (23:12:44 UTC)")
    vsetky = {f"d{k}": (f"{s} MNQ NT8", chyba) for k, s in enumerate(("vwaporbnet", "ibsentrynet", "vwapadxnet"))}
    assert n.report_issues({d: (p, "") for d, (p, _) in vsetky.items()}) == 0
    assert n.report_issues(vsetky) == 1
    assert bot.sent[0][1] == ("⚠️ <b>Nenabehli</b>: ibsentrynet MNQ NT8, vwapadxnet MNQ NT8, vwaporbnet MNQ NT8\n"
                              "<i>pripojenie 'Simulation' nie je Connected</i>")
    assert n.report_issues(vsetky) == 0
    assert n.report_issues({}) == 1 and bot.sent[-1][1].startswith("✅ <b>Znova v poriadku</b>: ibsentrynet MNQ NT8, ")


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
    assert "1. ▶ <b>US100 3m</b>" in text and "2. ▶ <b>MNQ 3m</b>" in text
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
    assert ctl.modes[INST] == "enabled" and "✓ US100 3m vwaporbnet: obchoduje" in bot.sent[-1][1]

    # iný proces už počúva na tom istom bote: príkazy sa vypnú, nič nepadne
    bot.fail = TelegramConflict("getUpdates: 409")
    assert cmd.poll() == 0 and cmd.disabled and cmd.poll() == 0


def test_auto_obnova_stavu_zap_vyp_pripnutie_a_zmazana_sprava(tmp_path: Path):
    bot, ctl = FakeBot(), FakeControls()
    t = [1000.0]
    state = TelegramState(tmp_path / "s.json")
    cmd = TelegramCommands(bot, CFG, state, ctl, clock=lambda: t[0])
    bot.ups = [cb("A:1", 1, mid=11)]
    cmd.poll()
    assert list(state.data["auto"]) == ["7:11"] and bot.pinned == {11}
    assert "⏱ auto 1 min" in bot.edited[-1][2] and bot.edited[-1][3][-1][-1]["callback_data"] == "A:0"
    assert cmd.refresh_auto() == 0                                  # ešte neuplynula minúta
    t[0] += 60
    assert cmd.refresh_auto() == 1 and bot.edited[-1][1] == 11 and "⏱ auto" in bot.edited[-1][2]
    # nová auto-obnova v tom istom chate vypne starú
    bot.ups = [cb("A:1", 2, mid=12)]
    cmd.poll()
    assert list(state.data["auto"]) == ["7:12"] and bot.pinned == {12}
    # odchod zo stavu (ponuka stratégie) auto-obnovu tej správy vypne, inak by ju prepísala späť
    bot.ups = [cb(f"m:{ikey(INST)}", 3, mid=12)]
    cmd.poll()
    assert state.data["auto"] == {} and bot.pinned == set()
    # vypnutie gombíkom; zmazaná správa z auto-obnovy vypadne sama
    bot.ups = [cb("A:1", 4, mid=13), cb("A:0", 5, mid=13)]
    cmd.poll()
    assert state.data["auto"] == {} and "⏱ Auto-obnova" in str(bot.edited[-1][3])
    bot.ups = [cb("A:1", 6, mid=14)]
    cmd.poll()
    t[0] += 60
    bot.edit_fail = TelegramError("editMessageText: 400 Bad Request: message to edit not found")
    assert cmd.refresh_auto() == 0 and state.data["auto"] == {}


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
    assert "vwaporbnet (MT5 · A):" in text                               # z akého účtu
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
    d = "vwaporbnet MNQ NT8"
    assert n.report_issues({"d1": (d, "nenabehla: pripojenie nie je Connected (23:09:44 UTC)")}) == 1
    assert n.report_issues({"d1": (d, "nenabehla: pripojenie nie je Connected (23:10:14 UTC)")}) == 0
    assert "UTC" not in bot.sent[0][1]


def test_jedno_kolo_jedna_sprava_za_vsetky_instancie(tmp_path: Path):
    root = tmp_path / "spool"
    bot = FakeBot()
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), bot, CFG, TelegramState(tmp_path / "s.json"))
    n.pump()
    for k in range(3):
        write(root, [hello(session=f"s{k}"), entry(2), fill(3, "in", 29152.0)], session=f"s{k}", inst=f"{INST}{k}")
    assert n.pump()["sent"] == 3 and len(bot.sent) == 1 and bot.sent[0][1].count("🟢") == 3


def test_notifikacie_len_z_vybranych_uctov_po_chatoch(tmp_path: Path):
    """🔔 Notifikácie: chat si vypne účet — obchody a súhrn štartu z neho nedostane, druhý chat áno."""
    root = tmp_path / "spool"
    t = [1000.0]
    bot, ctl = FakeBot(), FakeControls()
    cfg = TelegramConfig(token="t", chats=[7, 8], admins=[42])
    state = TelegramState(tmp_path / "s.json")
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), bot, cfg, state, clock=lambda: t[0])
    cmd = TelegramCommands(bot, cfg, state, ctl, clock=lambda: 1000.0)
    n.pump()

    # otázka ukáže účty zo stavu; ťuk vypne MT5 účet „A“ len v chate 7
    bot.ups = [msg("🔔 Notifikácie", uid=1)]
    cmd.poll()
    text, rows = bot.sent[-1][1], bot.sent[-1][2]
    assert "Z ktorých účtov" in text and "✅ MT5 · A" in text and "✅ NT8 · A" in text
    ucet = akey("mt5", "A")
    assert rows[0][0]["callback_data"] == f"N:{ucet}"
    bot.ups = [cb(f"N:{ucet}", 2)]
    cmd.poll()
    assert "🔕 MT5 · A" in bot.edited[-1][2] and state.muted(7) == {ucet: "MT5 · A"} and state.muted(8) == {}

    bot.sent.clear()
    akc = dict(hello(), account="A")
    write(root, [akc, entry(2), fill(3, "in", 29152.0)])
    write(root, [dict(akc, platform="ninjatrader"), entry(2), fill(3, "in", 21000.0)], inst="ninjatrader_A_MNQ_3m_x")
    n.pump()
    t[0] += 31
    n.pump()
    do7 = "\n".join(x[1] for x in bot.sent if x[0] == 7)
    do8 = "\n".join(x[1] for x in bot.sent if x[0] == 8)
    assert do7.count("🟢") == 1 and "NT8 · A" in do7 and "MT5 · A" not in do7 and "· MT5 ·" not in do7
    assert do8.count("🟢") == 2 and "▶️ <b>Spustené</b> · MT5" in do8 and "▶️ <b>Spustené</b> · NT8" in do8

    # Žiadny → nič, Všetky → späť; vypnutý účet, ktorý už nebeží, sa dá znova zapnúť
    bot.ups = [cb("N:-", 3)]
    cmd.poll()
    assert set(state.muted(7)) == {ucet, akey("ninjatrader", "A")}
    ctl.modes.clear()
    bot.ups = [cb("n", 4)]
    cmd.poll()
    assert "🔕 MT5 · A" in bot.edited[-1][2]
    bot.ups = [cb("N:*", 5)]
    cmd.poll()
    assert state.muted(7) == {} and "Žiadny účet" in bot.edited[-1][2]

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


def test_status_rozlisi_trh_zatvoreny_od_ticha_a_ping_nehlasi(tmp_path: Path):
    """Ping `hb` (docs/LIVE.md, „Ping“): /status ukáže 🟢 živá / 🌙 trh zatvorený / ⚪ ticho podľa pingu,
    nie len podľa barov; z pingu sa správa nerobí, a spool ho dá do stavu inštancie (`last_hb`)."""
    now = 1_800_000_000.0
    ms = int(now * 1000)

    class Ctl(FakeControls):
        def instances(self, now=None):
            base = {"tf": 3, "strategy": "vwaporbnet", "platform": "mt5", "account": "A", "ended": False,
                    "control": "enabled"}
            return [
                {**base, "instance": "mt5_A_BEZI_3m_x", "symbol": "BEZI", "last_t": ms - 20_000, "last_hb": ms - 20_000,
                 "last_bar_ms": ms - 200_000},
                {**base, "instance": "mt5_A_VIKEND_3m_x", "symbol": "VIKEND", "last_t": ms - 20_000, "last_hb": ms - 20_000,
                 "last_bar_ms": ms - 2 * 86_400_000},
                {**base, "instance": "mt5_A_PADOL_3m_x", "symbol": "PADOL", "last_t": ms - 600_000, "last_hb": ms - 600_000,
                 "last_bar_ms": ms - 2 * 86_400_000},
            ]

    cmd = TelegramCommands(FakeBot(), CFG, TelegramState(tmp_path / "s.json"), Ctl(), clock=lambda: now)
    riadky = cmd.status_view()[0].splitlines()
    # riadok so zdravím ide hneď pod riadok so symbolom
    stav = {s: riadky[next(k for k, x in enumerate(riadky) if f"<b>{s} 3m</b>" in x) + 1] for s in ("BEZI", "VIKEND", "PADOL")}
    assert "🟢 živá" in stav["BEZI"]
    assert "🌙 trh zatvorený" in stav["VIKEND"]
    assert "⚪ ticho 10 min" in stav["PADOL"]
    detail = cmd.instance_view(ikey("mt5_A_VIKEND_3m_x"))[0]
    assert "ping: teraz" in detail and "trh zatvorený" in detail

    # notifier: ping s rovnakým seq ako posledná udalosť správu nevyrobí ani neposunie stav
    root = tmp_path / "spool"
    write(root, [hello(), {"seq": 1, "t": 5, "k": "hb", "bars": 0, "lb": 0}])
    from tradebot.live.spool import latest_state

    st = latest_state([root])[0]
    assert st["last_hb"] == 5 and st["last_t"] == 5
    n = LiveNotifier(SpoolReader([root], tmp_path / "c.json"), FakeBot(), CFG, TelegramState(tmp_path / "s2.json"))
    b = SimpleNamespace(instance=INST, session="s1", path=root, events=[hello(), {"seq": 1, "t": 5, "k": "hb", "bars": 0, "lb": 0}])
    assert [s for s, _ in n.messages(b)] == [1]


def test_bez_admins_ovladanie_len_v_sukromnom_chate_a_pause_podla_videneho_statusu(tmp_path: Path):
    """Audit N-LIVE-18: prázdne `admins` dovolilo ovládať každému v skupine; `/pause N` bralo číslo
    z aktuálneho poradia, nie z /status, ktorý človek videl."""
    bot, ctl = FakeBot(), FakeControls()
    cfg = TelegramConfig(token="t", chats=[7, -100])
    cmd = TelegramCommands(bot, cfg, TelegramState(tmp_path / "s.json"), ctl, clock=lambda: 1000.0)
    bot.ups = [msg("/pause all", user=5, chat=-100, uid=1), msg("/status", user=5, chat=-100, uid=2)]
    cmd.poll()
    assert set(ctl.modes.values()) == {"enabled"} and "admini" in bot.sent[0][1]
    assert "<b>📊 Stav</b>" in bot.sent[1][1]                         # čítať v skupine smie
    bot.ups = [msg("/status", user=7, chat=7, uid=3)]                # súkromný chat: id chatu = id používateľa
    cmd.poll()
    novy = "mt5_1-A_AAA_3m_vwaporbnet"                              # pribudne pred ostatné, poradie sa posunie
    ctl.modes[novy] = "enabled"
    bot.ups = [msg("/pause 1", user=7, chat=7, uid=4)]
    cmd.poll()
    assert ctl.modes[novy] == "enabled" and ctl.modes[INST] == "paused"   # č. 1 z videného /status
