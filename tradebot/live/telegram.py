"""Telegram pre live obchodovanie (docs/LIVE.md, „Telegram“): správy z obchodného stroja a príkazy späť.

Beží v **agentovi** na stroji s platformami, nie v hube ani v adaptéri NT8/MT5:

- správy idú zo **spoolu** (`LiveNotifier`, vlastný kurzor `TELEGRAM_CURSOR`) — fungujú bez hubu
  aj bez webapp; agent dole = spool rastie a po reštarte sa správy dopošlú (kurzor sa posúva až
  po odoslaní, `(instance, session, seq)` už odoslaných sa neopakuje),
- príkazy (`TelegramCommands`, long-poll `getUpdates`) zapíšu **control súbor** platformy — ten
  istý mechanizmus ako pauza z webapp (EA aj NT8 ho čítajú do 2 s), takže v MQL5 ani C# nie je
  nič nové. Lokálne prepnutie sa zapamätá (`overrides`) a hubu ide v heartbeate, kým ho
  nezapíše do nasadenia — inak by webapp a platforma tvrdili niečo iné.

`getUpdates` smie na jednom bote volať **jediný proces** (inak Telegram vráti 409) — preto
príkazy prijíma len agent; strážca hubu (`tester.hub.telegram_watch`) len posiela.

Konfigurácia `TELEGRAM_CONFIG` (gitignored, tajomstvo)::

    {"token": "123:ABC", "chats": [123456789], "admins": [123456789],
     "commands": true, "signals": false, "notes": "warn", "label": "nas-win11"}

`chats` = kam ísť správy a odkiaľ sa berú príkazy; `admins` = id používateľov, ktorí smú
ovládať (prázdne = ktokoľvek z povolených chatov); `signals` = hlásiť aj zámery vstupu
(nielen vyplnenia); `notes` = najnižšia úroveň `note` (`info`/`warn`/`error`/`off`).
Env `TRADEBOT_TELEGRAM_TOKEN` a `TRADEBOT_TELEGRAM_CHATS` (čiarkou) prebijú súbor.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from tradebot.core.env import getenv

from .schema import CONTROL_MODES

__all__ = ["TelegramConfig", "TelegramBot", "TelegramError", "TelegramConflict", "TelegramState",
           "LiveNotifier", "TelegramCommands", "ControlFiles", "TelegramService", "format_event", "load_config"]

log = logging.getLogger(__name__)

API = "https://api.telegram.org"
#: Telegram pustí do jedného chatu zhruba 1 správu za sekundu; dlhšie správy sa delia.
MIN_SEND_INTERVAL = 1.05
MAX_TEXT = 3800
NOTE_LEVELS = {"info": 0, "warn": 1, "error": 2}


# --------------------------------------------------------------------------- #
# konfigurácia
# --------------------------------------------------------------------------- #

@dataclass
class TelegramConfig:
    token: str
    chats: list[int] = field(default_factory=list)
    admins: list[int] = field(default_factory=list)
    commands: bool = True
    signals: bool = False
    notes: str = "warn"
    label: str = ""

    def note_wanted(self, level: str) -> bool:
        prah = NOTE_LEVELS.get(self.notes)
        return prah is not None and NOTE_LEVELS.get(level, 1) >= prah


def _ids(value: Any) -> list[int]:
    if isinstance(value, str):
        value = [v for v in value.replace(";", ",").split(",") if v.strip()]
    elif isinstance(value, (int, float)):   # PowerShell 5.1 zapíše jednoprvkové pole ako číslo
        value = [value]
    out = []
    for v in value or []:
        try:
            out.append(int(str(v).strip()))
        except ValueError:
            log.warning("telegram: id %r nie je číslo — ignorujem", v)
    return out


def load_config(path: Path) -> TelegramConfig | None:
    """Config zo súboru a env; bez tokenu alebo bez chatu `None` (Telegram vypnutý)."""
    data: dict[str, Any] = {}
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data = raw
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        log.warning("telegram: %s sa nedá prečítať: %s", path, exc)
    token = getenv("TELEGRAM_TOKEN") or str(data.get("token") or "")
    chats = _ids(getenv("TELEGRAM_CHATS") or data.get("chats"))
    if not token or not chats:
        return None
    return TelegramConfig(token=token, chats=chats, admins=_ids(data.get("admins")),
                          commands=bool(data.get("commands", True)), signals=bool(data.get("signals", False)),
                          notes=str(data.get("notes") or "warn"), label=str(data.get("label") or ""))


# --------------------------------------------------------------------------- #
# Bot API
# --------------------------------------------------------------------------- #

class TelegramError(Exception):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TelegramConflict(TelegramError):
    """409: `getUpdates` na tomto bote už volá iný proces."""


class TelegramBot:
    """Tenký klient Bot API cez `urllib` (bez závislostí). `opener` sa dá podstrčiť v testoch:
    `opener(method, payload, timeout) -> dict` (telo odpovede Telegramu)."""

    def __init__(self, token: str, *, opener: Callable[[str, dict, float], dict] | None = None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 min_interval: float = MIN_SEND_INTERVAL) -> None:
        self.token = token
        self._opener = opener or self._urlopen
        self.clock = clock
        self.sleep = sleep
        self.min_interval = float(min_interval)
        self._last_send: dict[int, float] = {}
        self._lock = threading.Lock()

    def _urlopen(self, method: str, payload: dict, timeout: float) -> dict:
        req = urllib.request.Request(f"{API}/bot{self.token}/{method}", data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - pevná https adresa
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return json.loads(exc.read().decode("utf-8"))
            except (OSError, ValueError):
                return {"ok": False, "error_code": exc.code, "description": str(exc)}

    def call(self, method: str, payload: dict | None = None, timeout: float = 15.0) -> Any:
        try:
            body = self._opener(method, dict(payload or {}), timeout)
        except (OSError, ValueError) as exc:   # sieť, DNS, timeout
            raise TelegramError(f"{method}: {type(exc).__name__}: {exc}") from exc
        if body.get("ok"):
            return body.get("result")
        code = body.get("error_code")
        text = f"{method}: {code} {body.get('description') or ''}".strip()
        if code == 409:
            raise TelegramConflict(text)
        retry = (body.get("parameters") or {}).get("retry_after")
        raise TelegramError(text, float(retry) if retry else None)

    def send(self, chat_id: int, text: str, buttons: list[list[dict]] | None = None, *, html: bool = False,
             keyboard: list[list[str]] | None = None) -> Any:
        """Pošle text; drží odstup `min_interval` v jednom chate a na 429 raz počká `retry_after`.
        `buttons` = gombíky pod správou (inline), `keyboard` = stála klávesnica pod poľom na písanie,
        `html` = text je HTML (`<b>`, `<code>` …; volajúci escapuje)."""
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
        if html:
            payload["parse_mode"] = "HTML"
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        elif keyboard:
            payload["reply_markup"] = {"keyboard": [[{"text": t} for t in row] for row in keyboard],
                                       "resize_keyboard": True, "is_persistent": True}
        with self._lock:
            for pokus in range(2):
                cakaj = self._last_send.get(chat_id, -1e9) + self.min_interval - self.clock()
                if cakaj > 0:
                    self.sleep(cakaj)
                try:
                    out = self.call("sendMessage", payload)
                    self._last_send[chat_id] = self.clock()
                    return out
                except TelegramError as exc:
                    self._last_send[chat_id] = self.clock()
                    if exc.retry_after and pokus == 0 and exc.retry_after <= 60:
                        self.sleep(exc.retry_after)
                        continue
                    raise
        return None

    def updates(self, offset: int, timeout: int = 3) -> list[dict]:
        return list(self.call("getUpdates", {"offset": offset, "timeout": timeout,
                                             "allowed_updates": ["message", "callback_query"]},
                              timeout=timeout + 10) or [])

    def answer(self, callback_id: str, text: str = "") -> None:
        self.call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text[:200]})

    def edit(self, chat_id: int, message_id: int, text: str, buttons: list[list[dict]] | None = None, *,
             html: bool = False) -> None:
        """Prepíše správu (aj jej gombíky); „message is not modified“ (ten istý obsah) nie je chyba."""
        payload: dict[str, Any] = {"chat_id": chat_id, "message_id": message_id, "text": text[:4096],
                                   "disable_web_page_preview": True, "reply_markup": {"inline_keyboard": buttons or []}}
        if html:
            payload["parse_mode"] = "HTML"
        try:
            self.call("editMessageText", payload)
        except TelegramError as exc:
            if "not modified" not in str(exc):
                raise

    def set_commands(self, commands: list[tuple[str, str]]) -> None:
        """Menu „/“ v Telegrame (zoznam príkazov s popisom)."""
        self.call("setMyCommands", {"commands": [{"command": c, "description": d} for c, d in commands]})


# --------------------------------------------------------------------------- #
# stav na disku
# --------------------------------------------------------------------------- #

class TelegramState:
    """`ctx` (inštancia → hello + otvorené vstupy), `seq` (instance|session → posledné odoslané),
    `update_offset` (príkazy), `overrides` (lokálne prepnutia režimu), `issues` (nasadenie → chyba)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.data: dict[str, Any] = {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.data = raw
        except (OSError, ValueError):
            pass
        for k, default in (("ctx", {}), ("seq", {}), ("overrides", {}), ("issues", {})):
            if not isinstance(self.data.get(k), dict):
                self.data[k] = dict(default)
        self.data.setdefault("update_offset", 0)
        self.data.setdefault("initialized", False)
        self._lock = threading.RLock()

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self.path)

    def overrides(self) -> list[dict[str, Any]]:
        with self._lock:
            return [{"instance": k, **v} for k, v in sorted(self.data["overrides"].items())]

    def set_override(self, instance: str, mode: str, by: str, ts: float) -> None:
        with self._lock:
            self.data["overrides"][instance] = {"mode": mode, "by": by, "ts": ts}
            self.save()

    def drop_override(self, instance: str) -> None:
        with self._lock:
            if self.data["overrides"].pop(instance, None) is not None:
                self.save()


# --------------------------------------------------------------------------- #
# formát správ
# --------------------------------------------------------------------------- #

def _num(x: Any) -> str:
    if not isinstance(x, (int, float)):
        return "—"
    return f"{x:.2f}".rstrip("0").rstrip(".") if abs(x) >= 1 else f"{x:.6g}"


def _platform(p: Any) -> str:
    return {"ninjatrader": "NT8", "mt5": "MT5"}.get(str(p), str(p or "?"))


def _e(x: Any) -> str:
    return html.escape("" if x is None else str(x), quote=False)


def _sym(symbol: Any) -> str:
    """Symbol na čítanie: `US100.cash` → `US100` (Telegram by z bodky urobil odkaz), `MNQ 12-26` → `MNQ`."""
    return str(symbol or "?").split(" ", 1)[0].split(".", 1)[0]


def label(ctx: dict[str, Any]) -> str:
    """Krátke meno inštancie do správy (HTML): **US100** vwaporbnet · MT5 — účet a TF sú v /status."""
    return f"<b>{_e(_sym(ctx.get('symbol')))}</b> {_e(ctx.get('strategy') or '?')} · {_e(_platform(ctx.get('platform')))}"


def _side(d: Any) -> str:
    return "LONG" if d == 1 else "SHORT" if d == -1 else "?"


#: Najviac toľko zámerov vstupu si inštancia pamätá (staršie, ktoré nikdy nedostali cancel ani fill, odpadnú).
MAX_ENTRIES = 50

#: Životný cyklus (štart, koniec, reštart, zmena režimu) ide súhrnom, nie po udalostiach — `LiveNotifier`.
LIFECYCLE = ("hello", "bye", "control")


def format_event(ctx: dict[str, Any], ev: dict[str, Any], cfg: TelegramConfig) -> str | None:
    """Jedna udalosť spoolu → text správy v HTML (alebo None). Mení `ctx` — čakajúce vstupy (`entries`: entry →
    kým nepríde fill alebo cancel), otvorené pozície (`open`: fill in − out, SL/TP aj posuny `modify`) a poslednú
    cenu (`last_c` z baru) —, preto sa volá na každú udalosť v poradí, aj keď z nej správa nebude. Štart,
    koniec a režim (`LIFECYCLE`) tu správu nedávajú: zbiera ich notifier do súhrnu."""
    k = ev.get("k")
    if k == "bar":
        if isinstance(ev.get("c"), (int, float)):
            ctx["last_c"], ctx["last_bt"] = ev["c"], ev.get("bt")
        return None
    if k in LIFECYCLE:
        return None
    lab = label(ctx)
    if k == "note":
        level = str(ev.get("level") or "info")
        if not cfg.note_wanted(level):
            return None
        ikona = "🛑" if level == "error" else "⚠️" if level == "warn" else "ℹ️"
        return f"{ikona} {lab}\n{_e(ev.get('text') or '')}"
    if k == "order":
        p = ev.get("p") or {}
        oid = str(ev.get("id"))
        zamery = ctx.setdefault("entries", {})
        if ev.get("a") == "entry":
            zamery[oid] = {"dir": ev.get("dir") or p.get("dir"), "e": p.get("e"), "sl": p.get("sl"), "tp": p.get("tp"),
                           "q": p.get("q"), "ot": ev.get("ot"), "ready": bool(ev.get("ready")), "bt": ev.get("bt")}
            while len(zamery) > MAX_ENTRIES:
                zamery.pop(next(iter(zamery)))
            if cfg.signals and ev.get("ready"):
                return (f"📍 <b>Signál {_side(ev.get('dir') or p.get('dir'))}</b> {_e(ev.get('ot') or '')} "
                        f"@ {_num(p.get('e'))} × {_num(p.get('q'))}\n{lab} · SL {_num(p.get('sl'))} · TP {_num(p.get('tp'))}")
        elif ev.get("a") in ("cancel", "close"):
            zamery.pop(oid, None)
        elif ev.get("a") == "modify":
            pos = (ctx.get("open") or {}).get(oid)
            for kam in (pos, zamery.get(oid)):
                if kam is not None:
                    for f in ("sl", "tp"):
                        if isinstance(p.get(f), (int, float)):
                            kam[f] = p[f]
        return None
    if k == "fill":
        fid = str(ev.get("id") or "")
        price, qty = ev.get("price"), ev.get("qty")
        zamery = ctx.setdefault("entries", {})
        zamer = zamery.get(fid) or {}
        otvorene = ctx.setdefault("open", {})
        if ev.get("side") == "in":
            pos = otvorene.get(fid) or {"dir": zamer.get("dir"), "price": 0.0, "qty": 0.0,
                                        "sl": zamer.get("sl"), "tp": zamer.get("tp")}
            if isinstance(price, (int, float)) and isinstance(qty, (int, float)) and qty > 0:
                spolu = pos["qty"] + qty
                pos["price"] = (pos["price"] * pos["qty"] + price * qty) / spolu
                pos["qty"] = spolu
            otvorene[fid] = pos
            zamery.pop(fid, None)
            return (f"🟢 <b>VSTUP {_side(pos.get('dir'))}</b> × {_num(qty)} @ {_num(price)}\n"
                    f"{lab} · SL {_num(pos.get('sl'))} · TP {_num(pos.get('tp'))}")
        pos = otvorene.get(fid)
        vysledok, ikona = "", "⚪"
        if pos and pos.get("dir") in (1, -1) and isinstance(price, (int, float)) and isinstance(qty, (int, float)):
            body = (price - pos["price"]) * pos["dir"]
            pv = ctx.get("point_value")
            usd = body * qty * pv if isinstance(pv, (int, float)) else None
            vysledok = f" · <b>{usd:+.2f} $</b> ({body:+.2f} b)" if usd is not None else f" · <b>{body:+.2f} b</b>"
            ikona = "✅" if body > 0 else "❌" if body < 0 else "⚪"
            pos["qty"] = max(0.0, pos["qty"] - qty)
            if pos["qty"] <= 1e-9:
                otvorene.pop(fid, None)
        smer = f" {_side(pos.get('dir'))}" if pos else ""
        vystup = f" ({_e(ev.get('exit'))})" if ev.get("exit") else ""
        return f"{ikona} <b>VÝSTUP{smer}</b> × {_num(qty)} @ {_num(price)}{vysledok}\n{lab}{vystup}"
    return None


def _ctx_from_hello(ev: dict[str, Any]) -> dict[str, Any]:
    instr = ev.get("instrument") or {}
    return {"session": ev.get("session"), "platform": ev.get("platform"), "account": ev.get("account"),
            "symbol": ev.get("symbol"), "tf": ev.get("tf"), "strategy": ev.get("strategy"),
            "profile": ev.get("profile"), "tester": bool(ev.get("tester")),
            "point_value": instr.get("point_value"), "entries": {}, "open": {}}


def _first_hello(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, "rb") as fh:
            prvy = fh.readline()
        ev = json.loads(prvy) if prvy.endswith(b"\n") else None
    except (OSError, ValueError):
        return None
    return ev if isinstance(ev, dict) and ev.get("k") == "hello" else None


# --------------------------------------------------------------------------- #
# spool → správy
# --------------------------------------------------------------------------- #

#: Čas pokusu na konci chyby nasadenia — mení sa pri každom pokuse, na zmenu chyby nemá vplyv.
_ISSUE_TIME = re.compile(r" \(\d\d:\d\d:\d\d UTC\)$")


def _chunks(texty: list[str], sep: str = "\n") -> list[str]:
    """Riadky zlúčené do správ najviac `MAX_TEXT` znakov (Telegram pustí ~1 správu/s do chatu)."""
    out: list[str] = []
    for t in texty:
        if out and len(out[-1]) + len(sep) + len(t) <= MAX_TEXT:
            out[-1] += sep + t
        else:
            out.append(t)
    return out


#: Súhrn životného cyklu sa pošle, keď sa toľko sekúnd nič nové neudialo (reštart troch stratégií
#: trvá desiatky sekúnd) — alebo najneskôr po `LIFE_MAX` od prvej udalosti.
LIFE_QUIET = 30.0
LIFE_MAX = 180.0
#: Ako sa súhrn číta: druh → (ikona, nadpis); poradie = poradie riadkov.
LIFE_KINDS = {"restart": ("🔄", "Reštart"), "start": ("▶️", "Spustené"), "stop": ("⏹", "Zastavené"),
              "paused": ("⏸", "Pauza"), "enabled": ("▶️", "Obchoduje"), "flatten": ("⛔", "Flatten")}


def _issue_short(chyba: str) -> str:
    """Chyba nasadenia na čítanie: bez `nenabehla:`, bez detailu za „ — “ a bez „skúsim znova“."""
    t = _ISSUE_TIME.sub("", chyba or "")
    t = re.sub(r"^nenabehla:\s*", "", t).split(" — ", 1)[0]
    return re.sub(r"\s*-\s*sk[uú][sš]im znova nesk[oô]r\s*$", "", t).strip()


class LiveNotifier:
    """Udalosti spoolu → správy do všetkých `chats`. Prvý štart (bez stavu) prehrá históriu bez odosielania —
    správy začínajú „odteraz“. Obchody a varovania idú hneď (jedna správa za kolo), štart / koniec / reštart
    a zmena režimu sa zbierajú (`state["life"]`) a idú jedným súhrnom zoskupeným podľa platformy a symbolu."""

    def __init__(self, reader: Any, bot: TelegramBot, cfg: TelegramConfig, state: TelegramState, *,
                 clock: Callable[[], float] = time.time) -> None:
        self.reader = reader
        self.bot = bot
        self.cfg = cfg
        self.state = state
        self.clock = clock
        self.last_error: str | None = None
        self.sent_total = 0
        self._silent = False
        self.state.data.setdefault("life", {})

    def _skip_history(self) -> None:
        """História sa prehrá bez odosielania — zámery vstupov a otvorené pozície (P&L výstupu, ktorý príde
        až po zapnutí) sú potom známe, správy začínajú odteraz."""
        self._silent = True
        try:
            while True:
                batches = self.reader.read(5000)
                if not batches:
                    break
                for batch in batches:
                    riadky = self.messages(batch)
                    if riadky:
                        kluc = f"{batch.instance}|{batch.session}"
                        self.state["seq"][kluc] = max(int(self.state["seq"].get(kluc) or 0), riadky[-1][0])
                    self.reader.commit(batch)
        finally:
            self._silent = False
        self.state.data["initialized"] = True
        self.state.save()

    def _ctx(self, batch: Any, ev: dict[str, Any]) -> dict[str, Any]:
        ctxs = self.state["ctx"]
        if ev.get("k") == "hello":
            stary = ctxs.get(batch.instance) or {}
            novy = _ctx_from_hello(ev)
            if stary.get("session") == novy["session"]:   # rotácia dňa: ten istý beh, zámery ostávajú
                novy["entries"], novy["open"] = stary.get("entries") or {}, stary.get("open") or {}
                novy["_repeat"] = True
            elif not novy["tester"]:   # nový beh: pozícia u brokera trvá (reštart terminálu, prekompilovanie NT)
                novy["open"] = stary.get("open") or {}
            for k in ("last_c", "last_bt", "mode"):
                if k in stary:
                    novy.setdefault(k, stary[k])
            ctxs[batch.instance] = novy
            return novy
        ctx = ctxs.get(batch.instance)
        if ctx is None or ctx.get("session") != batch.session:
            hello = _first_hello(batch.path)
            novy = _ctx_from_hello(hello) if hello else {"session": batch.session, "entries": {}, "open": {}}
            if ctx is not None:
                for k in ("open", "last_c", "last_bt", "mode"):
                    if k in ctx and not novy.get(k):
                        novy[k] = ctx[k]
            ctx = ctxs[batch.instance] = novy
        return ctx

    def _life(self, instance: str, ctx: dict[str, Any], ev: dict[str, Any]) -> None:
        """Štart / koniec / režim do zbierky súhrnu. Režim sa hlási len pri zmene (EA ho potvrdzuje pri
        každom štarte); prvý známy `enabled` je bežný štart, nie správa."""
        k = ev.get("k")
        if k == "control":
            if ev.get("source") == "pending":
                return
            mode, predtym = ev.get("mode"), ctx.get("mode")
            ctx["mode"] = mode
            if mode == predtym or (predtym is None and mode == "enabled"):
                return
        if self._silent:
            return
        now = self.clock()
        z = self.state["life"].setdefault(instance, {"first": now, "seq": "", "mode": None, "reason": "",
                                                     "platform": ctx.get("platform"), "symbol": ctx.get("symbol"),
                                                     "strategy": ctx.get("strategy")})
        z["last"] = now
        for f in ("platform", "symbol", "strategy"):
            z[f] = ctx.get(f) or z.get(f)
        if k == "hello":
            z["seq"] += "h"
        elif k == "bye":
            z["seq"] += "b"
            z["reason"] = str(ev.get("reason") or "")
        else:
            z["mode"] = ev.get("mode")

    def messages(self, batch: Any) -> list[tuple[int, str]]:
        """`(seq, text)` z dávky; udalosti už odoslané (`seq` ≤ uložené) a behy v Testeri sa preskočia.
        Štart, koniec a režim idú do zbierky súhrnu (text prázdny)."""
        kluc = f"{batch.instance}|{batch.session}"
        hotovo = int(self.state["seq"].get(kluc) or 0)
        out = []
        for ev in batch.events:
            ctx = self._ctx(batch, ev)
            seq = int(ev.get("seq") or 0)
            if ctx.get("tester") or seq <= hotovo:
                continue
            if ev.get("k") in LIFECYCLE:
                if not (ev.get("k") == "hello" and ctx.pop("_repeat", False)):
                    self._life(batch.instance, ctx, ev)
                out.append((seq, ""))
                continue
            out.append((seq, format_event(ctx, ev, self.cfg) or ""))
        return out

    def life_summary(self, force: bool = False) -> str | None:
        """Zozbieraný životný cyklus ako jedna správa, keď je čas (ticho `LIFE_QUIET`, alebo `LIFE_MAX` od prvej
        udalosti, alebo `force`); inak None. Reštart = koniec a znova štart v jednej zbierke."""
        zb: dict[str, dict[str, Any]] = self.state["life"]
        if not zb:
            return None
        now = self.clock()
        if not force and now - max(z["last"] for z in zb.values()) < LIFE_QUIET \
                and now - min(z["first"] for z in zb.values()) < LIFE_MAX:
            return None
        skupiny: dict[tuple[str, str, str], list[str]] = {}
        for z in zb.values():
            seq = z.get("seq") or ""
            druhy = []
            if seq:
                druhy.append("restart" if seq.endswith("h") and "b" in seq else "start" if seq.endswith("h") else "stop")
            if z.get("mode"):
                druhy.append(str(z["mode"]))
            for d in druhy:
                kluc = (d, _platform(z.get("platform")), _sym(z.get("symbol")))
                meno = str(z.get("strategy") or "?") + (f" ({z['reason']})" if d == "stop" and z.get("reason") else "")
                skupiny.setdefault(kluc, []).append(meno)
        poradie = list(LIFE_KINDS)
        riadky = []
        for (d, plat, sym), mena in sorted(skupiny.items(), key=lambda kv: (poradie.index(kv[0][0]) if kv[0][0] in poradie else 99, kv[0][1], kv[0][2])):
            ikona, nadpis = LIFE_KINDS.get(d, ("•", d))
            riadky.append(f"{ikona} <b>{nadpis}</b> · {_e(plat)} · <b>{_e(sym)}</b>: {_e(', '.join(sorted(mena)))}")
        return "\n".join(riadky) or None

    def _send_all(self, text: str) -> None:
        for chat in self.cfg.chats:
            self.bot.send(chat, text, html=True)

    def pump(self, max_events: int = 500) -> dict[str, Any]:
        """Jedno kolo: prečítaj, pošli, potvrď. Obchody a varovania z celého kola idú jednou správou (každý
        obchod vlastný odsek); súhrn životného cyklu, keď dozrel. Chyba Telegramu = kurzor stojí, ďalšie kolo
        to pošle znova (odoslané `seq` sa nezdvojí)."""
        if not self.state.data.get("initialized"):
            self._skip_history()
            return {"sent": 0, "skipped_history": True}
        sent = 0
        batches = self.reader.read(max_events)
        riadky_po: list[tuple[Any, list[tuple[int, str]]]] = [(b, self.messages(b)) for b in batches]
        texty = [t for _, riadky in riadky_po for _, t in riadky if t]
        try:
            for text in _chunks(texty, sep="\n\n"):
                self._send_all(text)
            sent += len(texty)
            suhrn = self.life_summary()
            if suhrn:
                self._send_all(suhrn)
                self.state.data["life"] = {}
                sent += suhrn.count("\n") + 1
        except TelegramError as exc:
            self.last_error = str(exc)
            self.state.save()
            return {"sent": sent, "error": self.last_error}
        for batch, riadky in riadky_po:
            if riadky:
                kluc = f"{batch.instance}|{batch.session}"
                self.state["seq"][kluc] = max(int(self.state["seq"].get(kluc) or 0), riadky[-1][0])
            self.reader.commit(batch)
        if batches or sent:
            self.state.save()
        self.last_error = None
        self.sent_total += sent
        return {"sent": sent, "error": None}

    def report_issues(self, issues: dict[str, tuple[str, str]]) -> int:
        """Chyby nasadení z reconcilera (`dep → (popis, chyba)`) zoskupené podľa príčiny: nová/zmenená chyba =
        „⚠ Nenabehli: a, b, c — príčina“, zmiznutá = „✅ Znova v poriadku: a, b“. Čas pokusu, detail a „skúsim
        znova“ sa do porovnania ani do správy nedávajú. Telegram dole = skúsi sa nabudúce (stav sa nezmení)."""
        stare: dict[str, list[str]] = self.state["issues"]
        nove: dict[str, list[str]] = {}
        zle: dict[str, list[str]] = {}
        for dep, (popis, chyba) in issues.items():
            kratka = _issue_short(chyba or "")
            if kratka:
                nove[dep] = [popis, kratka]
                if (stare.get(dep) or ["", ""])[1] != kratka:
                    zle.setdefault(kratka, []).append(popis)
        dobre = sorted(popis for dep, (popis, _) in stare.items() if dep not in nove)
        spravy = [f"⚠️ <b>Nenabehli</b>: {_e(', '.join(sorted(mena)))}\n<i>{_e(pricina)}</i>" for pricina, mena in zle.items()]
        if dobre:
            spravy.append(f"✅ <b>Znova v poriadku</b>: {_e(', '.join(dobre))}")
        if not spravy:
            return 0
        try:
            self._send_all("\n\n".join(spravy))
        except TelegramError as exc:
            self.last_error = str(exc)
            return 0
        self.state.data["issues"] = nove
        self.state.save()
        return len(spravy)


# --------------------------------------------------------------------------- #
# príkazy → control súbor
# --------------------------------------------------------------------------- #

#: Inštancia bez udalosti dlhšie než toľko dní sa v /status ani v ponuke neukazuje (víkend + sviatok sa zmestí).
STALE_DAYS = 7


class ControlFiles:
    """Inštancie na tomto stroji (spool) a ich control súbory — MT5 `Common/Files`, NT `Documents/NinjaTrader 8`."""

    def __init__(self, roots: Callable[[], list[Path]]) -> None:
        self.roots = roots

    @staticmethod
    def _platform_dir(instance: str) -> tuple[str, Path | None]:
        if instance.startswith("mt5_"):
            from tradebot.adapters.mt5.__main__ import find_common_files

            return "mt5", find_common_files()
        if instance.startswith("ninjatrader_"):
            from tradebot.adapters.ninjatrader.__main__ import find_nt_user_dir

            return "ninjatrader", find_nt_user_dir()
        return "", None

    def read(self, instance: str) -> dict | None:
        plat, d = self._platform_dir(instance)
        if d is None:
            return None
        try:
            if plat == "mt5":
                from tradebot.adapters.mt5.__main__ import read_control
            else:
                from tradebot.adapters.ninjatrader.__main__ import read_control
            return read_control(d, instance)
        except Exception:  # noqa: BLE001 - poškodený súbor = neznámy režim, nie pád príkazu
            return {"mode": "?"}

    def instances(self, now: float | None = None, stale_days: float = STALE_DAYS) -> list[dict[str, Any]]:
        """Inštancie zo spoolu s režimom z control súboru, zoradené platforma → účet → symbol. Bez udalosti
        dlhšie než `stale_days` (staré behy, odstránené nasadenia) sa vynechajú — spool ostáva na disku."""
        from .spool import latest_state

        hranica = ((now if now is not None else time.time()) - stale_days * 86400) * 1000
        out = []
        for st in latest_state(self.roots()):
            if not st.get("last_t") or st["last_t"] < hranica:
                continue
            c = self.read(st["instance"])
            st["control"] = (c or {}).get("mode") or "enabled"
            out.append(st)
        return sorted(out, key=lambda s: (str(s.get("platform")), str(s.get("account")), str(s.get("symbol")),
                                          str(s.get("strategy")), s["instance"]))

    def set_mode(self, instance: str, mode: str, by: str) -> dict:
        if mode not in CONTROL_MODES:
            raise ValueError(f"režim {mode!r}")
        plat, d = self._platform_dir(instance)
        if d is None:
            raise ValueError(f"platforma inštancie {instance} na tomto stroji nie je")
        if plat == "mt5":
            from tradebot.adapters.mt5.__main__ import write_control

            return write_control(d, instance, mode, None, by=by)
        from tradebot.adapters.ninjatrader.__main__ import write_control

        return write_control(d, instance, mode=mode, by=by)


HELP = ("Ovládanie gombíkmi pod správou alebo v klávesnici dole:\n"
        "📊 Stav — stratégie po platformách, ťuknutím na stratégiu pauza / spustenie / flatten\n"
        "📋 Ordery — otvorené pozície a čakajúce vstupy\n\n"
        "Aj ako príkazy: /status, /orders, /pause <č|časť mena|all>, /resume <…>, /flatten <…> (s potvrdením)")

#: Stála klávesnica pod poľom na písanie; text gombíka = príkaz.
MENU = [["📊 Stav", "📋 Ordery"], ["❓ Pomoc"]]
MENU_TEXT = {"📊 Stav": "/status", "📋 Ordery": "/orders", "❓ Pomoc": "/help"}
#: Menu „/“ (setMyCommands).
BOT_COMMANDS = [("status", "stav stratégií s gombíkmi"), ("orders", "otvorené pozície a čakajúce vstupy"),
                ("pause", "pauza: /pause <č|meno|all>"), ("resume", "obchodovať: /resume <č|meno|all>"),
                ("flatten", "zavrieť pozície: /flatten <č|meno|all>"), ("help", "pomoc")]
MODE_ICON = {"enabled": "▶", "paused": "⏸", "flatten": "⛔"}
MODE_TEXT = {"enabled": "obchoduje", "paused": "pauza", "flatten": "flatten"}
#: Potvrdenie flattenu platí toľko sekúnd.
CONFIRM_SECONDS = 120


def ikey(instance: str) -> str:
    """Krátky kľúč inštancie do `callback_data` (Telegram ho drží do 64 bajtov, id inštancie býva ~50)."""
    return format(zlib.crc32(instance.encode("utf-8")) & 0xFFFFFFFF, "08x")


def _age(ms: Any, now: float) -> str:
    if not isinstance(ms, (int, float)):
        return "—"
    m = max(0, int((now * 1000 - ms) / 60000))
    if m < 1:
        return "teraz"
    if m < 60:
        return f"{m} min"
    if m < 48 * 60:
        return f"{m // 60} h {m % 60} min" if m % 60 and m < 600 else f"{m // 60} h"
    return f"{m // 1440} d"


def _alive(st: dict[str, Any], now: float) -> bool:
    """Ako karta Live: posledná udalosť do 3 barov TF."""
    tf = max(1, int(st.get("tf") or 1))
    return bool(st.get("last_t")) and now * 1000 - st["last_t"] <= 3 * tf * 60000


def _short(st: dict[str, Any]) -> str:
    return f"{_sym(st.get('symbol'))} {st.get('tf') or '?'}m {st.get('strategy') or '?'}"


def _positions(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"id": k, **v} for k, v in (ctx.get("open") or {}).items() if (v.get("qty") or 0) > 1e-9]


def _pending(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"id": k, **v} for k, v in (ctx.get("entries") or {}).items() if v.get("ready")]


def _pos_text(pos: dict[str, Any], ctx: dict[str, Any]) -> str:
    out = f"{_side(pos.get('dir'))} {_num(pos.get('qty'))} @ {_num(pos.get('price'))}"
    if pos.get("sl") is not None or pos.get("tp") is not None:
        out += f" · SL {_num(pos.get('sl'))} TP {_num(pos.get('tp'))}"
    c, pv = ctx.get("last_c"), ctx.get("point_value")
    if isinstance(c, (int, float)) and pos.get("dir") in (1, -1):
        body = (c - pos["price"]) * pos["dir"]
        usd = f", {body * pos['qty'] * pv:+.2f} $" if isinstance(pv, (int, float)) else ""
        out += f" · teraz {_num(c)} ({body:+.2f} b{usd})"
    return out


class TelegramCommands:
    """`getUpdates` → príkaz alebo gombík → control súbor. Prijíma len z `cfg.chats` a (ak sú) od `cfg.admins`.

    Gombíky (`callback_data`): `s` stav, `o` ordery, `m:<kľúč>` ponuka stratégie, `P:`/`R:<kľúč|*>` pauza /
    spustenie, `F:<kľúč|*>` otázka na flatten, `X:<čas>:<kľúč|*>` potvrdený flatten (`*` = všetky)."""

    def __init__(self, bot: TelegramBot, cfg: TelegramConfig, state: TelegramState, controls: ControlFiles,
                 *, clock: Callable[[], float] = time.time, on_change: Callable[[], None] | None = None) -> None:
        self.bot = bot
        self.cfg = cfg
        self.state = state
        self.controls = controls
        self.clock = clock
        self.on_change = on_change
        self.disabled: str | None = None

    def _allowed(self, chat: Any, user: Any) -> bool:
        return chat in self.cfg.chats and (not self.cfg.admins or user in self.cfg.admins)

    def poll(self, timeout: int = 3) -> int:
        """Jedno kolo long-pollu; vráti počet spracovaných aktualizácií. 409 = príkazy sa vypnú (iný proces
        na tom istom bote) — správy idú ďalej."""
        if self.disabled:
            return 0
        try:
            ups = self.bot.updates(int(self.state.data.get("update_offset") or 0), timeout)
        except TelegramConflict as exc:
            self.disabled = f"príkazy vypnuté: na bote už počúva iný proces ({exc})"
            log.warning("telegram: %s", self.disabled)
            return 0
        for u in ups:
            try:
                self.handle(u)
            except Exception as exc:  # noqa: BLE001 - zlý príkaz nesmie zastaviť počúvanie
                log.warning("telegram: aktualizácia %s: %s: %s", u.get("update_id"), type(exc).__name__, exc)
            self.state.data["update_offset"] = int(u.get("update_id") or 0) + 1
        if ups:
            self.state.save()
        return len(ups)

    # -- vstup ------------------------------------------------------------- #

    def handle(self, u: dict[str, Any]) -> None:
        if "callback_query" in u:
            self._callback(u["callback_query"])
            return
        msg = u.get("message") or {}
        chat, user = (msg.get("chat") or {}).get("id"), (msg.get("from") or {}).get("id")
        text = str(msg.get("text") or "").strip()
        text = MENU_TEXT.get(text, text)
        if not text.startswith("/"):
            return
        if not self._allowed(chat, user):
            log.warning("telegram: príkaz z nepovoleného chatu %s / používateľa %s ignorovaný", chat, user)
            return
        cmd, _, arg = text.partition(" ")
        cmd = cmd.split("@", 1)[0].lower()
        if cmd in ("/start", "/help"):
            self.bot.send(chat, HELP, keyboard=MENU)
        elif cmd == "/status":
            t, b = self.status_view()
            self.bot.send(chat, t, b, html=True)
        elif cmd == "/orders":
            t, b = self.orders_view()
            self.bot.send(chat, t, b, html=True)
        elif cmd in ("/pause", "/resume"):
            self.bot.send(chat, self._apply(arg, "paused" if cmd == "/pause" else "enabled", user))
        elif cmd == "/flatten":
            ciel = self._targets(arg)
            if isinstance(ciel, str):
                self.bot.send(chat, ciel)
                return
            t, b = self.flatten_view("*" if arg.strip().lower() == "all" else ikey(ciel[0]["instance"]), ciel)
            self.bot.send(chat, t, b, html=True)
        else:
            self.bot.send(chat, f"Neznámy príkaz {cmd}.\n\n{HELP}", keyboard=MENU)

    def _callback(self, q: dict[str, Any]) -> None:
        msg = q.get("message") or {}
        chat, user = (msg.get("chat") or {}).get("id"), (q.get("from") or {}).get("id")
        if not self._allowed(chat, user):
            self.bot.answer(q.get("id", ""), "nepovolené")
            return
        data = str(q.get("data") or "")
        akcia, _, kluc = data.partition(":")
        oznam = ""
        if akcia == "o":
            t, b = self.orders_view()
        elif akcia == "m":
            t, b = self.instance_view(kluc)
        elif akcia in ("P", "R"):
            mode = "paused" if akcia == "P" else "enabled"
            oznam = self._apply_keys(kluc, mode, user)
            t, b = self.status_view(oznam) if kluc == "*" else self.instance_view(kluc, oznam)
        elif akcia == "F":
            t, b = self.flatten_view(kluc)
        elif akcia in ("X", "flatten"):   # `flatten:<čas>:<id>` = gombík zo starej správy
            ts, _, ciel = kluc.partition(":")
            if self.clock() - float(ts or 0) > CONFIRM_SECONDS:
                oznam = "Potvrdenie vypršalo — skús znova."
            elif akcia == "flatten" and ciel != "*":
                oznam = self._apply(ciel, "flatten", user, exact=True)
            else:
                oznam = self._apply_keys(ciel, "flatten", user)
            t, b = self.status_view(oznam)
        else:   # `s`, `cancel`, neznáme
            t, b = self.status_view()
        self.bot.answer(q.get("id", ""), oznam.split("\n", 1)[0][:200] if oznam else "")
        if msg.get("message_id") is not None:
            self.bot.edit(chat, msg["message_id"], t, b, html=True)

    # -- ciele a zápis ------------------------------------------------------ #

    def _by_key(self, kluc: str) -> list[dict[str, Any]]:
        inst = self.controls.instances(self.clock())
        if kluc == "*":
            return [i for i in inst if not i.get("ended")]
        return [i for i in inst if ikey(i["instance"]) == kluc]

    def _targets(self, arg: str, exact: bool = False) -> list[dict[str, Any]] | str:
        inst = self.controls.instances(self.clock())
        a = arg.strip()
        if not a:
            return "Ktorú? Napíš číslo zo /status, časť mena alebo all — alebo použi 📊 Stav a gombíky."
        if a.lower() == "all":
            return [i for i in inst if not i.get("ended")] or "Žiadna bežiaca inštancia."
        if exact:
            hit = [i for i in inst if i["instance"] == a]
        elif a.isdigit() and 1 <= int(a) <= len(inst):
            hit = [inst[int(a) - 1]]
        else:
            hit = [i for i in inst if a.lower() in i["instance"].lower()]
        if not hit:
            return f"Inštanciu „{a}“ nepoznám — pozri /status."
        if len(hit) > 1:
            return "Viac zhôd:\n" + "\n".join(f"• {i['instance']}" for i in hit) + "\nUpresni."
        return hit

    def _write(self, ciel: list[dict[str, Any]], mode: str, user: Any) -> list[str]:
        by = f"telegram:{user}"
        riadky = []
        for i in ciel:
            try:
                self.controls.set_mode(i["instance"], mode, by)
                self.state.set_override(i["instance"], mode, by, self.clock())
                riadky.append(f"✓ {_short(i)}: {MODE_TEXT.get(mode, mode)}")
            except Exception as exc:  # noqa: BLE001
                riadky.append(f"✗ {_short(i)}: {exc}")
        if ciel and self.on_change:
            self.on_change()
        return riadky

    def _apply(self, arg: str, mode: str, user: Any, exact: bool = False) -> str:
        ciel = self._targets(arg, exact=exact)
        if isinstance(ciel, str):
            return ciel
        return "\n".join(self._write(ciel, mode, user)) + "\n(platforma to prevezme do ~2 s)"

    def _apply_keys(self, kluc: str, mode: str, user: Any) -> str:
        ciel = self._by_key(kluc)
        return "\n".join(self._write(ciel, mode, user)) if ciel else "Stratégiu už nevidím — obnov stav."

    # -- pohľady (text HTML + gombíky) -------------------------------------- #

    def _ctx(self, instance: str) -> dict[str, Any]:
        return (self.state.data.get("ctx") or {}).get(instance) or {}

    def status_view(self, oznam: str = "") -> tuple[str, list[list[dict]]]:
        now = self.clock()
        inst = self.controls.instances(now)
        hlava = f"<b>📊 Stav</b>{' · ' + _e(self.cfg.label) if self.cfg.label else ''} · {time.strftime('%H:%M', time.localtime(now))}"
        if not inst:
            return hlava + "\n\nŽiadna stratégia za posledných 7 dní.", [[{"text": "🔄 Obnoviť", "callback_data": "s"}]]
        riadky, skupina = [hlava], None
        for n, i in enumerate(inst, 1):
            g = (i.get("platform"), i.get("account"))
            if g != skupina:
                skupina = g
                riadky.append(f"\n<b>{_e(_platform(i.get('platform')))}</b> · {_e(i.get('account'))}")
            ctx = self._ctx(i["instance"])
            if i.get("ended"):
                zdravie = "⏹ skončila"
            elif _alive(i, now):
                zdravie = "🟢 živá"
            else:
                zdravie = f"⚪ ticho {_age(i.get('last_t'), now)}"
            poz = _positions(ctx)
            pozicia = " · " + ", ".join(f"{_side(x.get('dir'))} {_num(x.get('qty'))}" for x in poz) if poz else ""
            cak = len(_pending(ctx))
            riadky.append(f"{n}. {MODE_ICON.get(i.get('control'), '?')} <b>{_e(_sym(i.get('symbol')))} {_e(i.get('tf'))}m</b> "
                          f"{_e(i.get('strategy'))}\n      {zdravie} · bar {_age(i.get('last_bar_ms'), now)}{_e(pozicia)}"
                          f"{f' · čaká {cak}' if cak else ''}")
        riadky.append("\n▶ obchoduje · ⏸ pauza · ⛔ flatten — ťukni na stratégiu")
        if oznam:
            riadky.append("\n" + _e(oznam))
        gomb = [{"text": f"{n}. {_sym(i.get('symbol'))} {i.get('strategy')}"[:40], "callback_data": f"m:{ikey(i['instance'])}"}
                for n, i in enumerate(inst, 1)]
        rows = [gomb[k:k + 2] for k in range(0, len(gomb), 2)]
        rows.append([{"text": "⏸ Pauza všetkým", "callback_data": "P:*"}, {"text": "▶ Spustiť všetky", "callback_data": "R:*"}])
        rows.append([{"text": "🔄 Obnoviť", "callback_data": "s"}, {"text": "📋 Ordery", "callback_data": "o"}])
        return "\n".join(riadky), rows

    def instance_view(self, kluc: str, oznam: str = "") -> tuple[str, list[list[dict]]]:
        now = self.clock()
        hit = self._by_key(kluc)
        if not hit:
            return "Stratégiu už nevidím (skončila alebo je stará).", [[{"text": "⬅ Späť", "callback_data": "s"}]]
        i = hit[0]
        ctx = self._ctx(i["instance"])
        riadky = [f"<b>{_e(_short(i))}</b>",
                  f"{_e(_platform(i.get('platform')))} · {_e(i.get('account'))} · profil {_e(i.get('profile') or '—')}",
                  f"Režim: {MODE_ICON.get(i.get('control'), '?')} {_e(MODE_TEXT.get(i.get('control'), i.get('control')))}",
                  f"Posledný bar: {_age(i.get('last_bar_ms'), now)} · udalosť: {_age(i.get('last_t'), now)}"
                  + (" · skončila" if i.get("ended") else "")]
        poz = _positions(ctx)
        riadky.append("Pozície: " + ("; ".join(_e(_pos_text(x, ctx)) for x in poz) if poz else "žiadne"))
        cak = _pending(ctx)
        if cak:
            riadky.append("Čakajúce vstupy: " + "; ".join(
                _e(f"{_side(x.get('dir'))} {x.get('ot') or ''} @ {_num(x.get('e'))} × {_num(x.get('q'))}") for x in cak))
        if oznam:
            riadky.append("\n" + _e(oznam))
        k = ikey(i["instance"])
        rows = [[{"text": "⏸ Pauza", "callback_data": f"P:{k}"}, {"text": "▶ Spustiť", "callback_data": f"R:{k}"}],
                [{"text": "⛔ Flatten…", "callback_data": f"F:{k}"}],
                [{"text": "⬅ Späť", "callback_data": "s"}, {"text": "🔄", "callback_data": f"m:{k}"}]]
        return "\n".join(riadky), rows

    def flatten_view(self, kluc: str, ciel: list[dict[str, Any]] | None = None) -> tuple[str, list[list[dict]]]:
        ciel = ciel if ciel is not None else self._by_key(kluc)
        if not ciel:
            return "Stratégiu už nevidím.", [[{"text": "⬅ Späť", "callback_data": "s"}]]
        mena = "\n".join(f"• {_e(_short(i))} ({_e(_platform(i.get('platform')))})" for i in ciel)
        spat = "s" if kluc == "*" else f"m:{kluc}"
        return (f"<b>⛔ Flatten</b> zruší čakajúce vstupy a <b>zavrie pozície</b>:\n{mena}\n\nPotvrď do 2 minút.",
                [[{"text": "⛔ Áno, zavrieť", "callback_data": f"X:{int(self.clock())}:{kluc}"},
                  {"text": "Zrušiť", "callback_data": spat}]])

    def orders_view(self) -> tuple[str, list[list[dict]]]:
        now = self.clock()
        inst = self.controls.instances(now)
        poz, cak = [], []
        for i in inst:
            ctx = self._ctx(i["instance"])
            meno = f"<b>{_e(_sym(i.get('symbol')))}</b> {_e(i.get('strategy'))} ({_e(_platform(i.get('platform')))})"
            poz += [f"• {meno}: {_e(_pos_text(x, ctx))}" for x in _positions(ctx)]
            cak += [f"• {meno}: {_e(_side(x.get('dir')))} {_e(x.get('ot') or '')} @ {_e(_num(x.get('e')))} "
                    f"SL {_e(_num(x.get('sl')))} TP {_e(_num(x.get('tp')))} × {_e(_num(x.get('q')))}" for x in _pending(ctx)]
        text = (f"<b>📋 Ordery</b> · {time.strftime('%H:%M', time.localtime(now))}\n\n<b>Otvorené pozície</b>\n"
                + ("\n".join(poz) if poz else "žiadne")
                + "\n\n<b>Čakajúce vstupy</b>\n" + ("\n".join(cak) if cak else "žiadne")
                + "\n\n<i>Podľa telemetrie zo spoolu (vstupy − výstupy); pri výpadku telemetrie sa môže líšiť od brokera.</i>")
        return text, [[{"text": "🔄 Obnoviť", "callback_data": "o"}, {"text": "📊 Stav", "callback_data": "s"}]]

    def status_text(self) -> str:
        """Stav ako obyčajný text (bez HTML) — pre volajúcich, ktorí gombíky nechcú."""
        return re.sub(r"<[^>]+>", "", html.unescape(self.status_view()[0]))


# --------------------------------------------------------------------------- #
# služba v agentovi
# --------------------------------------------------------------------------- #

#: Ako často sa znova hľadajú korene spoolu a pozrú chyby nasadení.
ROOTS_RECHECK_SECONDS = 60.0
ISSUES_SECONDS = 30.0


class TelegramService:
    """Správy + príkazy v jednom vlákne agenta: `tick(wait)` = pošli, čo pribudlo v spoole, raz za
    `ISSUES_SECONDS` chyby nasadení, potom long-poll príkazov (`wait` s), ktorý slúži aj ako čakanie.
    `roots` = korene spoolu, `issues` = `dep → (popis, chyba)` z reconcilera, `on_change` = príkaz
    zmenil režim (agent hneď znova zosúladí nasadenia s prekrytím)."""

    def __init__(self, cfg: TelegramConfig, state_path: Path, cursor_path: Path, *,
                 roots: Callable[[], list[Path]], issues: Callable[[], dict[str, tuple[str, str]]] | None = None,
                 on_change: Callable[[], None] | None = None, bot: TelegramBot | None = None,
                 clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep) -> None:
        self.cfg = cfg
        self.bot = bot or TelegramBot(cfg.token)
        self.state = TelegramState(state_path)
        self.cursor_path = Path(cursor_path)
        self._roots_fn = roots
        self._roots: list[Path] = []
        self._roots_at: float | None = None
        self.issues = issues
        self.clock = clock
        self.sleep = sleep
        self._issues_at: float | None = None
        self.notifier: LiveNotifier | None = None
        self.controls = ControlFiles(self.roots)
        self.commands = (TelegramCommands(self.bot, cfg, self.state, self.controls, clock=clock, on_change=on_change)
                         if cfg.commands else None)
        self._menu_set = False

    def roots(self) -> list[Path]:
        now = self.clock()
        if self._roots_at is None or now - self._roots_at >= ROOTS_RECHECK_SECONDS:
            self._roots_at = now
            try:
                self._roots = list(self._roots_fn())
            except Exception as exc:  # noqa: BLE001
                log.debug("telegram: korene spoolu: %s", exc)
        return self._roots

    def _notifier(self) -> LiveNotifier | None:
        roots = self.roots()
        if not roots:
            self.notifier = None
            return None
        if self.notifier is None or [str(r) for r in self.notifier.reader.roots] != [str(r) for r in roots]:
            from .spool import SpoolReader

            self.notifier = LiveNotifier(SpoolReader(roots, self.cursor_path), self.bot, self.cfg, self.state,
                                         clock=self.clock)
        return self.notifier

    def tick(self, wait: float = 3.0) -> None:
        n = self._notifier()
        if n is not None:
            r = n.pump()
            if r.get("error"):
                log.warning("telegram: správy sa nedajú poslať: %s", r["error"])
        now = self.clock()
        if self.issues is not None and n is not None and (self._issues_at is None or now - self._issues_at >= ISSUES_SECONDS):
            self._issues_at = now
            try:
                n.report_issues(self.issues())
            except Exception as exc:  # noqa: BLE001
                log.debug("telegram: chyby nasadení: %s", exc)
        if self.commands is not None and not self._menu_set:
            try:
                self.bot.set_commands(BOT_COMMANDS)
                self._menu_set = True
            except TelegramError as exc:
                log.debug("telegram: setMyCommands: %s", exc)
        if self.commands is not None and not self.commands.disabled:
            try:
                self.commands.poll(int(max(1, wait)))
                return
            except TelegramError as exc:
                log.debug("telegram: getUpdates: %s", exc)
        self.sleep(wait)

    def status(self) -> dict[str, Any]:
        return {"chats": len(self.cfg.chats), "commands": self.commands is not None,
                "commands_error": self.commands.disabled if self.commands else None,
                "last_error": self.notifier.last_error if self.notifier else None,
                "sent_total": self.notifier.sent_total if self.notifier else 0,
                "overrides": self.state.overrides()}
