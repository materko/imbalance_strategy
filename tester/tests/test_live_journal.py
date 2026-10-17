"""Denník obchodov agenta a Telegram 🧾 Obchody / 📈 Výkon / pohľady hubu (docs/LIVE.md, „Telegram“)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from tradebot.live import perf
from tradebot.live.journal import JournalBuilder, TradeJournal
from tradebot.live.reports import perf_chart, perf_view, trades_view
from tradebot.live.spool import SpoolReader
from tradebot.live.telegram import (MENU, TelegramBot, TelegramCommands, TelegramConfig, TelegramState, _multipart,
                                    format_event, ikey, load_config)

INST = "mt5_1514925336-FTMO-Demo_US100.cash_3m_vwaporbnet"
INST2 = "ninjatrader_Sim101_MNQ 12-26_3m_ibsnet"
T0 = 1_790_000_000_000   # ms


def hello(seq=1, session="s1", inst=INST, tester=False):
    mt5 = inst.startswith("mt5")
    return {"seq": seq, "t": T0, "k": "hello", "schema": 1, "platform": "mt5" if mt5 else "ninjatrader",
            "account": "1514925336-FTMO-Demo" if mt5 else "Sim101", "symbol": "US100.cash" if mt5 else "MNQ 12-26",
            "tf": 3, "strategy": "vwaporbnet" if mt5 else "ibsnet", "profile": "P1", "session": session,
            "tester": tester, "instrument": {"point_value": 1.0 if mt5 else 2.0}}


def entry(seq, oid, d=1, e=100.0, ready=True, t=0):
    return {"seq": seq, "t": T0 + t, "k": "order", "bt": 1, "ready": ready, "a": "entry", "id": oid, "dir": d,
            "ot": "limit", "p": {"dir": d, "e": e, "sl": e - 10 * d, "tp": e + 20 * d, "q": 1}}


def cancel(seq, oid, t=0):
    return {"seq": seq, "t": T0 + t, "k": "order", "bt": 1, "ready": True, "a": "cancel", "id": oid, "r": "expired"}


def fill(seq, oid, side, price, qty=1.0, exit_="", t=0):
    return {"seq": seq, "t": T0 + t, "k": "fill", "ft": T0 + t, "id": oid, "side": side, "exit": exit_,
            "price": price, "qty": qty, "ready": True}


def write(root: Path, events: list[dict], session="s1", inst=INST) -> None:
    d = root / inst
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"20261016-064928_{session}.jsonl", "a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")


def _builder(tmp: Path) -> tuple[JournalBuilder, TradeJournal]:
    j = TradeJournal(tmp / "journal.jsonl")
    return JournalBuilder(SpoolReader([tmp / "spool"], tmp / "jcur.json"), j, tmp / "jstate.json"), j


def _history(root: Path) -> None:
    """US100: výhra +10, prehra −5, zrušený, predhistória (ready false); MNQ: výhra +3 b × 2 $ × 2 ks."""
    write(root, [hello(), entry(2, "a", ready=False), entry(3, "a"), fill(4, "a", "in", 100.0, t=60_000),
                 fill(5, "a", "out", 110.0, exit_="sltp", t=120_000),
                 entry(6, "b", d=-1, e=200.0, t=180_000), fill(7, "b", "in", 200.0, t=200_000),
                 fill(8, "b", "out", 205.0, exit_="sltp", t=300_000),
                 entry(9, "c", t=400_000), cancel(10, "c", t=500_000)])
    write(root, [hello(inst=INST2), entry(2, "x", e=50.0, t=600_000), fill(3, "x", "in", 50.0, qty=2, t=610_000),
                 fill(4, "x", "out", 53.0, qty=2, exit_="Profit target", t=700_000)], inst=INST2)


def test_format_event_zapise_zaznamy_s_pnl():
    ctx = {"platform": "mt5", "symbol": "US100.cash", "strategy": "vwaporbnet", "point_value": 1.0}
    rec: list[dict] = []
    cfg = TelegramConfig(token="t")
    format_event(ctx, entry(2, "a", ready=False), cfg, rec.append)     # predhistória nie
    format_event(ctx, entry(3, "a"), cfg, rec.append)
    format_event(ctx, fill(4, "a", "in", 100.0), cfg, rec.append)
    format_event(ctx, fill(5, "a", "out", 104.0, qty=0.5, exit_="tp1"), cfg, rec.append)
    format_event(ctx, fill(6, "a", "out", 96.0, qty=0.5, exit_="sl"), cfg, rec.append)
    format_event(ctx, entry(7, "b"), cfg, rec.append)
    format_event(ctx, cancel(8, "b"), cfg, rec.append)
    assert [r["k"] for r in rec] == ["entry", "in", "out", "out", "entry", "cancel"]
    assert rec[2]["usd"] == 2.0 and rec[2]["left"] == 0.5 and rec[3]["usd"] == -2.0 and rec[3]["left"] == 0.0
    assert rec[5]["r"] == "expired"
    tr = perf.trades([{**r, "instance": "i", "t": n} for n, r in enumerate(rec)])
    assert len(tr) == 1 and tr[0]["usd"] == 0.0 and tr[0]["exits"] == ["tp1", "sl"]   # čiastočné výstupy = 1 obchod


def test_dennik_prejde_celu_historiu_raz_a_tester_vynecha(tmp_path: Path):
    root = tmp_path / "spool"
    _history(root)
    write(root, [hello(session="t1", tester=True), entry(2, "z"), fill(3, "z", "in", 1.0)], session="t1")
    b, j = _builder(tmp_path)
    assert b.pump()["written"] == 11
    recs = j.read()
    assert {r["k"] for r in recs} == {"entry", "in", "out", "cancel"}
    assert all(r["session"] != "t1" for r in recs) and recs[0]["strategy"] == "vwaporbnet"
    assert b.pump()["written"] == 0
    # nový proces nad tým istým stavom nič neopakuje, nové udalosti doplní
    write(root, [entry(11, "d", t=800_000)])
    b2, _ = _builder(tmp_path)
    assert b2.pump()["written"] == 1 and len(j.read()) == 12
    # pád medzi zápisom a stavom: riadok dvakrát v súbore, čítanie ho dá raz
    j.append([recs[0]])
    assert len(j.read()) == 12


def test_vykon_ako_v_testeri_a_kapital(tmp_path: Path):
    root = tmp_path / "spool"
    _history(root)
    b, j = _builder(tmp_path)
    b.pump()
    tr = perf.trades(j.read())
    assert [t["usd"] for t in tr] == [10.0, -5.0, 12.0]
    s = perf.summary(tr, capital=1000.0)
    assert (s["trades"], s["wins"], s["losses"], s["winrate"]) == (3, 2, 1, 66.67)
    assert s["pnl_abs"] == 17.0 and s["pnl_pct"] == 1.7 and s["profit_factor"] == 4.4
    assert s["max_drawdown_abs"] == 5.0 and s["streaks"] == {"wins": 1, "losses": 1}
    assert s["exits"] == {"sltp": 2, "Profit target": 1} and s["final_balance"] == 1017.0
    assert perf.capital_for({"FTMO": 5000, "*": 1000}, {"1514925336-FTMO-Demo"}) == 5000.0
    assert perf.capital_for({"FTMO": 5000, "*": 1000}, {"1514925336-FTMO-Demo", "Sim101"}) == 6000.0
    assert perf.capital_for({"FTMO": 5000}, {"Sim101"}) is None and perf.capital_for(100, {"a", "b"}) == 200.0


def test_telegram_obchody_vykon_graf(tmp_path: Path):
    root = tmp_path / "spool"
    _history(root)
    b, j = _builder(tmp_path)
    b.pump()
    recs = j.read()
    now = (T0 + 800_000) / 1000
    text, rows = trades_view(recs, "*", ikey)
    assert text.startswith("<b>🧾 Obchody</b> · všetky stratégie")
    riadky = text.split("\n")
    assert riadky[1].startswith("✅") and "MNQ" in riadky[1] and "+12.00 $" in riadky[1] and "(Profit target)" in riadky[1]
    assert riadky[2].startswith("🚫") and "zrušený LONG limit @ 100 (expired)" in riadky[2]
    assert riadky[3].startswith("❌") and "-5.00 $" in riadky[3]
    assert any(g["callback_data"] == f"tr:{ikey(INST)}" for r in rows for g in r)
    text, rows = perf_view(recs, "a", "*", {"*": 1000}, ikey, now)
    assert "Obchody <b>3</b> · ✅ 2 / ❌ 1" in text and "winrate <b>66.7 %</b>" in text
    assert "+17.00 $</b> (+0.85 %)" in text            # kapitál dvoch účtov = 2000
    assert "<b>Po stratégiách</b>" in text and "• <b>MNQ</b> ibsnet NT8 · 1 obch. · 100 % · +12.00 $ (+1.20 %)" in text
    assert rows[0][3]["text"] == "• Všetko"
    text, _ = perf_view(recs, "a", ikey(INST), None, ikey, now)
    assert "Obchody <b>2</b>" in text and "Po stratégiách" not in text and "capital" in text
    text, _ = perf_view(recs, "d", "*", None, ikey, now + 3 * 86400)
    assert "žiadny uzavretý obchod" in text
    png, popis = perf_chart(recs, "a", "*", None, ikey, now)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and "3 obchodov" in popis


class Bot:
    def __init__(self):
        self.sent, self.photos, self.edited, self.answered = [], [], [], []

    def send(self, chat, text, buttons=None, html=False, keyboard=None):
        self.sent.append((chat, text, buttons or keyboard))

    def send_photo(self, chat, png, caption="", buttons=None):
        self.photos.append((chat, png[:4], caption))

    def edit(self, chat, mid, text, buttons=None, html=False):
        self.edited.append((chat, mid, text, buttons))

    def answer(self, cid, text=""):
        self.answered.append(text)


class Controls:
    def instances(self, now=None):
        return []


class Hub:
    def __init__(self):
        self.down = False
        self.calls = 0

    def views(self):
        self.calls += 1
        if self.down:
            raise OSError("hub dole")
        return [{"plugin": "ff_calendar", "view": "upcoming", "label": "📅 Udalosti"}]

    def view(self, plugin, view):
        if self.down:
            raise OSError("hub dole")
        return f"<b>{plugin}/{view}</b>"


def _cmd(tmp: Path, hub=None):
    root = tmp / "spool"
    _history(root)
    b, j = _builder(tmp)
    b.pump()
    bot = Bot()
    cfg = TelegramConfig(token="t", chats=[7], capital=1000)
    c = TelegramCommands(bot, cfg, TelegramState(tmp / "tg.json"), Controls(), journal=j, hub=hub,
                         clock=lambda: (T0 + 800_000) / 1000)
    return c, bot


def _msg(text, uid=1):
    return {"update_id": uid, "message": {"chat": {"id": 7}, "from": {"id": 42}, "text": text}}


def _cb(data, uid=2):
    return {"update_id": uid, "callback_query": {"id": "q", "data": data, "from": {"id": 42},
                                                 "message": {"chat": {"id": 7}, "message_id": 5}}}


def test_klavesnica_gombiky_obchody_vykon_graf_a_pohlady_hubu(tmp_path: Path):
    hub = Hub()
    c, bot = _cmd(tmp_path, hub)
    c.handle(_msg("/start"))
    klav = bot.sent[-1][2]
    assert klav[:2] == MENU[:2] and klav[-1] == ["📅 Udalosti", "❓ Pomoc"]
    c.handle(_msg("🧾 Obchody"))
    assert bot.sent[-1][1].startswith("<b>🧾 Obchody</b>")
    c.handle(_msg("📈 Výkon"))
    assert bot.sent[-1][1].startswith("<b>📈 Výkon</b> · 30 dní")
    c.handle(_cb("pf:a:*"))
    assert "Všetko" in bot.edited[-1][2] and "(+0.85 %)" in bot.edited[-1][2]
    c.handle(_cb(f"tr:{ikey(INST2)}"))
    assert "MNQ ibsnet" in bot.edited[-1][2]
    c.handle(_cb("gr:a:*"))
    assert bot.photos[-1][1] == b"\x89PNG" and bot.answered[-1] == "graf odoslaný"
    c.handle(_msg("📅 Udalosti"))
    assert bot.sent[-1][1] == "<b>ff_calendar/upcoming</b>"
    c.handle(_cb("v:ff_calendar:upcoming"))
    assert bot.edited[-1][2] == "<b>ff_calendar/upcoming</b>"
    hub.down = True
    c.handle(_cb("v:ff_calendar:upcoming"))
    assert bot.edited[-1][2].startswith("Hub nedostupný")
    c._hub_views_at -= 1000            # pohľady znova, hub dole = posledné známe ostávajú
    assert c.menu()[-1] == ["📅 Udalosti", "❓ Pomoc"] and hub.calls == 2


def test_bez_hubu_a_bez_dennika(tmp_path: Path):
    bot = Bot()
    c = TelegramCommands(bot, TelegramConfig(token="t", chats=[7]), TelegramState(tmp_path / "tg.json"), Controls())
    c.handle(_msg("/start"))
    assert bot.sent[-1][2] == MENU
    c.handle(_msg("/perf"))
    assert "nebeží" in bot.sent[-1][1]
    c.handle(_msg("/hub"))
    assert "nie je pripojený" in bot.sent[-1][1]


def test_send_photo_multipart_a_capital_v_configu(tmp_path: Path):
    volania = []
    bot = TelegramBot("t", opener=lambda m, p, t: (volania.append((m, p)), {"ok": True, "result": {}})[1],
                      sleep=lambda s: None)
    bot.send_photo(7, b"\x89PNG", "<b>x</b>", [[{"text": "a", "callback_data": "b"}]])
    assert volania[0][0] == "sendPhoto" and volania[0][1]["photo"] == b"\x89PNG"
    data, ctype = _multipart(volania[0][1])
    hranica = ctype.split("boundary=", 1)[1]
    assert data.startswith(f"--{hranica}\r\n".encode()) and b'filename="photo.png"' in data
    assert b'{"inline_keyboard": [[{"text": "a", "callback_data": "b"}]]}' in data
    (tmp_path / "tg.json").write_text(json.dumps({"token": "t", "chats": [1], "capital": {"*": 5000}}), encoding="utf-8")
    assert load_config(tmp_path / "tg.json").capital == {"*": 5000}


def test_hub_pohlady_pluginov_cez_api(tmp_path: Path):
    from fastapi.testclient import TestClient

    from tester.hub.plugins import HubPlugin, PluginHost
    from tester.hub.server import HubState, create_hub_app

    class Kal(HubPlugin):
        def views(self):
            return {"upcoming": "📅 Udalosti"}

        def view(self, name):
            return "<b>udalosti</b>"

    st = HubState(root=tmp_path / "hub", token=None)
    app = create_hub_app(st)
    st.plugins = PluginHost(tmp_path / "hub" / "plugins", st, None, classes={"kal": Kal}, clock=time.time)
    cl = TestClient(app)
    assert cl.get("/api/plugins/views").json() == [{"plugin": "kal", "view": "upcoming", "label": "📅 Udalosti"}]
    assert cl.get("/api/plugins/kal/views/upcoming").json() == {"text": "<b>udalosti</b>"}
    assert cl.get("/api/plugins/kal/views/nic").status_code == 404
    (tmp_path / "hub" / "plugins" / "kal").mkdir(parents=True)
    (tmp_path / "hub" / "plugins" / "kal" / "config.json").write_text('{"enabled": false}', encoding="utf-8")
    assert cl.get("/api/plugins/views").json() == []
