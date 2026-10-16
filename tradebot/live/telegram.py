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

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
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

    def send(self, chat_id: int, text: str, buttons: list[list[dict]] | None = None) -> Any:
        """Pošle text (bez parse_mode — nič sa neescapuje); drží odstup `min_interval` v jednom chate
        a na 429 raz počká `retry_after`."""
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
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

    def edit(self, chat_id: int, message_id: int, text: str) -> None:
        self.call("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text[:4096]})


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


def label(ctx: dict[str, Any]) -> str:
    tf = f" {ctx['tf']}m" if ctx.get("tf") else ""
    return f"{ctx.get('symbol') or '?'}{tf} {ctx.get('strategy') or '?'} · {_platform(ctx.get('platform'))} {ctx.get('account') or ''}".rstrip()


def _side(d: Any) -> str:
    return "LONG" if d == 1 else "SHORT" if d == -1 else "?"


def format_event(ctx: dict[str, Any], ev: dict[str, Any], cfg: TelegramConfig) -> str | None:
    """Jedna udalosť spoolu → text správy (alebo None). Mení `ctx` (zámery vstupov, otvorené pozície),
    preto sa volá na každú udalosť v poradí, aj keď z nej správa nebude."""
    k = ev.get("k")
    lab = label(ctx)
    if k == "hello":
        return f"▶ {lab} beží (profil {ev.get('profile') or '—'})"
    if k == "bye":
        return f"⏹ {lab} skončila ({ev.get('reason') or 'bez dôvodu'})"
    if k == "control":
        if ev.get("source") == "pending":
            return None
        m = ev.get("mode")
        ikona = {"enabled": "▶ obchoduje", "paused": "⏸ pauza — nové vstupy sa neposielajú",
                 "flatten": "⛔ flatten — ruší vstupy a zatvára pozície"}.get(m, str(m))
        return f"{ikona} · {lab}"
    if k == "note":
        level = str(ev.get("level") or "info")
        if not cfg.note_wanted(level):
            return None
        return f"{'🛑' if level == 'error' else '⚠' if level == 'warn' else 'ℹ'} {lab}: {ev.get('text') or ''}"
    if k == "order":
        p = ev.get("p") or {}
        if ev.get("a") == "entry":
            ctx.setdefault("entries", {})[str(ev.get("id"))] = {"dir": ev.get("dir") or p.get("dir"),
                                                               "sl": p.get("sl"), "tp": p.get("tp")}
            if cfg.signals and ev.get("ready"):
                return (f"📍 signál {_side(ev.get('dir') or p.get('dir'))} {ev.get('ot') or ''} @ {_num(p.get('e'))} "
                        f"SL {_num(p.get('sl'))} TP {_num(p.get('tp'))} × {_num(p.get('q'))} · {lab}")
        return None
    if k == "fill":
        fid = str(ev.get("id") or "")
        price, qty = ev.get("price"), ev.get("qty")
        zamer = (ctx.get("entries") or {}).get(fid) or {}
        otvorene = ctx.setdefault("open", {})
        if ev.get("side") == "in":
            pos = otvorene.get(fid) or {"dir": zamer.get("dir"), "price": 0.0, "qty": 0.0}
            if isinstance(price, (int, float)) and isinstance(qty, (int, float)) and qty > 0:
                spolu = pos["qty"] + qty
                pos["price"] = (pos["price"] * pos["qty"] + price * qty) / spolu
                pos["qty"] = spolu
            otvorene[fid] = pos
            return (f"🟢 VSTUP {_side(pos.get('dir'))} × {_num(qty)} @ {_num(price)} "
                    f"(SL {_num(zamer.get('sl'))}, TP {_num(zamer.get('tp'))}) · {lab}")
        pos = otvorene.get(fid)
        vysledok = ""
        ikona = "⚪"
        if pos and pos.get("dir") in (1, -1) and isinstance(price, (int, float)) and isinstance(qty, (int, float)):
            body = (price - pos["price"]) * pos["dir"]
            pv = ctx.get("point_value")
            usd = body * qty * pv if isinstance(pv, (int, float)) else None
            vysledok = f" ({body:+.2f} b" + (f", {usd:+.2f} $)" if usd is not None else ")")
            ikona = "✅" if body > 0 else "❌" if body < 0 else "⚪"
            pos["qty"] = max(0.0, pos["qty"] - qty)
            if pos["qty"] <= 1e-9:
                otvorene.pop(fid, None)
        smer = _side(pos.get("dir")) + " " if pos else ""
        return f"{ikona} VÝSTUP {ev.get('exit') or ''} {smer}× {_num(qty)} @ {_num(price)}{vysledok} · {lab}".replace("  ", " ")
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

def _chunks(texty: list[str]) -> list[str]:
    """Riadky zlúčené do správ najviac `MAX_TEXT` znakov (Telegram pustí ~1 správu/s do chatu)."""
    out: list[str] = []
    for t in texty:
        if out and len(out[-1]) + 1 + len(t) <= MAX_TEXT:
            out[-1] += "\n" + t
        else:
            out.append(t)
    return out


class LiveNotifier:
    """Udalosti spoolu → správy do všetkých `chats`. Prvý štart (bez stavu) preskočí históriu na koniec
    súborov — správy začínajú „odteraz“, nie stovkami starých obchodov."""

    def __init__(self, reader: Any, bot: TelegramBot, cfg: TelegramConfig, state: TelegramState) -> None:
        self.reader = reader
        self.bot = bot
        self.cfg = cfg
        self.state = state
        self.last_error: str | None = None
        self.sent_total = 0

    def _skip_history(self) -> None:
        """História sa prehrá bez odosielania — zámery vstupov a otvorené pozície (P&L výstupu, ktorý príde
        až po zapnutí) sú potom známe, správy začínajú odteraz."""
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
            ctxs[batch.instance] = novy
            return novy
        ctx = ctxs.get(batch.instance)
        if ctx is None or ctx.get("session") != batch.session:
            hello = _first_hello(batch.path)
            ctx = _ctx_from_hello(hello) if hello else {"session": batch.session, "entries": {}, "open": {}}
            ctxs[batch.instance] = ctx
        return ctx

    def messages(self, batch: Any) -> list[tuple[int, str]]:
        """`(seq, text)` z dávky; udalosti už odoslané (`seq` ≤ uložené) a behy v Testeri sa preskočia."""
        kluc = f"{batch.instance}|{batch.session}"
        hotovo = int(self.state["seq"].get(kluc) or 0)
        out = []
        for ev in batch.events:
            ctx = self._ctx(batch, ev)
            seq = int(ev.get("seq") or 0)
            if ctx.get("tester") or seq <= hotovo:
                continue
            if ev.get("k") == "hello" and ctx.pop("_repeat", False):
                out.append((seq, ""))
                continue
            out.append((seq, format_event(ctx, ev, self.cfg) or ""))
        return out

    def _send_all(self, text: str) -> None:
        if self.cfg.label:
            text = f"[{self.cfg.label}] {text}"
        for chat in self.cfg.chats:
            self.bot.send(chat, text)

    def pump(self, max_events: int = 500) -> dict[str, Any]:
        """Jedno kolo: prečítaj, pošli, potvrď. Chyba Telegramu = kurzor stojí na prvej neodoslanej
        udalosti (už odoslané si pamätá `seq`), ďalšie kolo pokračuje."""
        if not self.state.data.get("initialized"):
            self._skip_history()
            return {"sent": 0, "skipped_history": True}
        sent = 0
        try:
            for batch in self.reader.read(max_events):
                kluc = f"{batch.instance}|{batch.session}"
                riadky = self.messages(batch)
                for text in _chunks([t for _, t in riadky if t]):
                    self._send_all(text)
                    sent += text.count("\n") + 1
                if riadky:
                    self.state["seq"][kluc] = max(int(self.state["seq"].get(kluc) or 0), riadky[-1][0])
                self.state.save()
                self.reader.commit(batch)
        except TelegramError as exc:
            self.last_error = str(exc)
            self.state.save()
            return {"sent": sent, "error": self.last_error}
        self.last_error = None
        self.sent_total += sent
        return {"sent": sent, "error": None}

    def report_issues(self, issues: dict[str, tuple[str, str]]) -> int:
        """Chyby nasadení z reconcilera (`dep → (popis, chyba)`): nová/zmenená chyba = správa, zmiznutá =
        „v poriadku“. Vráti počet správ; Telegram dole = skúsi sa nabudúce (stav sa nezmení)."""
        stare: dict[str, list[str]] = self.state["issues"]
        spravy, nove = [], {}
        for dep, (popis, chyba) in issues.items():
            if chyba:
                nove[dep] = [popis, chyba]
                if (stare.get(dep) or ["", ""])[1] != chyba:
                    spravy.append(f"⚠ nasadenie {popis}: {chyba}")
        for dep, (popis, _) in stare.items():
            if dep not in nove:
                spravy.append(f"✅ nasadenie {popis} je v poriadku")
        if not spravy:
            return 0
        try:
            self._send_all("\n".join(spravy))
        except TelegramError as exc:
            self.last_error = str(exc)
            return 0
        self.state.data["issues"] = nove
        self.state.save()
        return len(spravy)


# --------------------------------------------------------------------------- #
# príkazy → control súbor
# --------------------------------------------------------------------------- #

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

    def instances(self) -> list[dict[str, Any]]:
        from .spool import latest_state

        out = []
        for st in sorted(latest_state(self.roots()), key=lambda s: s["instance"]):
            c = self.read(st["instance"])
            st["control"] = (c or {}).get("mode") or "enabled"
            out.append(st)
        return out

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


HELP = ("Príkazy:\n/status — inštancie, režim, posledný bar\n/pause <č|časť mena|all> — bez nových vstupov\n"
        "/resume <…> — obchodovať\n/flatten <…> — zrušiť vstupy a zavrieť pozície (s potvrdením)")


class TelegramCommands:
    """`getUpdates` → príkaz → control súbor. Prijíma len z `cfg.chats` a (ak sú) od `cfg.admins`."""

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

    def handle(self, u: dict[str, Any]) -> None:
        if "callback_query" in u:
            self._callback(u["callback_query"])
            return
        msg = u.get("message") or {}
        chat, user = (msg.get("chat") or {}).get("id"), (msg.get("from") or {}).get("id")
        text = str(msg.get("text") or "").strip()
        if not text.startswith("/"):
            return
        if not self._allowed(chat, user):
            log.warning("telegram: príkaz z nepovoleného chatu %s / používateľa %s ignorovaný", chat, user)
            return
        cmd, _, arg = text.partition(" ")
        cmd = cmd.split("@", 1)[0].lower()
        if cmd in ("/start", "/help"):
            self.bot.send(chat, HELP)
        elif cmd == "/status":
            self.bot.send(chat, self.status_text())
        elif cmd in ("/pause", "/resume"):
            self.bot.send(chat, self._apply(arg, "paused" if cmd == "/pause" else "enabled", user))
        elif cmd == "/flatten":
            ciel = self._targets(arg)
            if isinstance(ciel, str):
                self.bot.send(chat, ciel)
                return
            kluc = "*" if arg.strip().lower() == "all" else ciel[0]["instance"]
            mena = "\n".join(f"• {i['instance']}" for i in ciel)
            self.bot.send(chat, f"Flatten zruší čakajúce vstupy a ZAVRIE pozície:\n{mena}\nPotvrď do 2 minút.",
                          buttons=[[{"text": "⛔ Áno, flatten", "callback_data": f"flatten:{int(self.clock())}:{kluc}"},
                                    {"text": "Zrušiť", "callback_data": "cancel"}]])
        else:
            self.bot.send(chat, f"Neznámy príkaz {cmd}.\n{HELP}")

    def _callback(self, q: dict[str, Any]) -> None:
        msg = q.get("message") or {}
        chat, user = (msg.get("chat") or {}).get("id"), (q.get("from") or {}).get("id")
        if not self._allowed(chat, user):
            self.bot.answer(q.get("id", ""), "nepovolené")
            return
        data = str(q.get("data") or "")
        if data.startswith("flatten:"):
            _, ts, kluc = data.split(":", 2)
            if self.clock() - float(ts) > 120:
                text = "Potvrdenie vypršalo — pošli /flatten znova."
            else:
                text = self._apply("all" if kluc == "*" else kluc, "flatten", user, exact=kluc != "*")
        else:
            text = "Zrušené."
        self.bot.answer(q.get("id", ""))
        if msg.get("message_id") is not None:
            self.bot.edit(chat, msg["message_id"], text)

    def _targets(self, arg: str, exact: bool = False) -> list[dict[str, Any]] | str:
        inst = self.controls.instances()
        a = arg.strip()
        if not a:
            return "Ktorú? Napíš číslo zo /status, časť mena alebo all."
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

    def _apply(self, arg: str, mode: str, user: Any, exact: bool = False) -> str:
        ciel = self._targets(arg, exact=exact)
        if isinstance(ciel, str):
            return ciel
        by = f"telegram:{user}"
        riadky = []
        for i in ciel:
            try:
                self.controls.set_mode(i["instance"], mode, by)
                self.state.set_override(i["instance"], mode, by, self.clock())
                riadky.append(f"✓ {i['instance']}: {mode}")
            except Exception as exc:  # noqa: BLE001
                riadky.append(f"✗ {i['instance']}: {exc}")
        if self.on_change:
            self.on_change()
        return "\n".join(riadky) + "\n(platforma to prevezme do ~2 s; potvrdenie príde ako správa)"

    def status_text(self) -> str:
        inst = self.controls.instances()
        if not inst:
            return "Na tomto stroji nie je žiadna inštancia v spoole."
        now = self.clock()
        riadky = []
        for n, i in enumerate(inst, 1):
            bar = i.get("last_bar_ms")
            vek = f"bar pred {int((now * 1000 - bar) / 60000)} min" if isinstance(bar, (int, float)) else "bez baru"
            ikona = {"enabled": "▶", "paused": "⏸", "flatten": "⛔"}.get(i.get("control"), "?")
            koniec = " · skončila" if i.get("ended") else ""
            riadky.append(f"{n}. {ikona} {i.get('symbol')} {i.get('tf')}m {i.get('strategy')} · "
                          f"{_platform(i.get('platform'))} {i.get('account')} · {vek}{koniec}")
        return "\n".join(riadky)


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

            self.notifier = LiveNotifier(SpoolReader(roots, self.cursor_path), self.bot, self.cfg, self.state)
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
