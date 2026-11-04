"""Klient Telegram Bot API a config bota (docs/LIVE.md, „Telegram“) — zdieľaný agentom aj hubom.

Telegram agenta (správy zo spoolu, príkazy, 📈 Výkon) je **plugin agenta** `tester/hub/agent_plugins/telegram/`;
hub posiela správy pluginov (`tester.hub.plugins.HubNotifier`). Oba používajú tento modul: `TelegramBot`
(tenký klient cez `urllib`, odstup ~1 správa/s, 429), `TelegramConfig` a `load_config` (súbor + env
`TRADEBOT_TELEGRAM_TOKEN` / `_CHATS`). Zmena tu je zmena rozhrania — plugin agenta sa po nej nenačíta
za behu, agent aj hub sa reštartujú (`tester.hub.pluginreload`).

Konfigurácia (gitignored, tajomstvo)::

    {"token": "123:ABC", "chats": [123456789], "admins": [123456789],
     "commands": true, "signals": false, "notes": "warn", "label": "nas-win11",
     "capital": {"1514925336": 100000, "*": 50000}}

Význam polí pre agenta opisuje `tester.hub.agent_plugins.telegram.service`; hub z nich berie `token`,
`chats` a `label`.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from tradebot.core.env import getenv

__all__ = ["TelegramConfig", "TelegramBot", "TelegramError", "TelegramConflict", "load_config", "MAX_TEXT",
           "API"]

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
    capital: Any = None

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
                          notes=str(data.get("notes") or "warn"), label=str(data.get("label") or ""),
                          capital=data.get("capital"))


# --------------------------------------------------------------------------- #
# Bot API
# --------------------------------------------------------------------------- #

def _multipart(payload: dict) -> tuple[bytes, str]:
    """`multipart/form-data` pre `sendPhoto`: bajty = súbor, objekty = JSON, ostatné = text."""
    hranica = f"tradebot{zlib.crc32(repr(sorted(payload)).encode()) & 0xFFFFFFFF:08x}{int(time.time() * 1000)}"
    crlf = "\r\n"
    casti: list[bytes] = []
    for k, v in payload.items():
        if isinstance(v, (bytes, bytearray)):
            hlava = (f"--{hranica}{crlf}Content-Disposition: form-data; name=\"{k}\"; filename=\"{k}.png\"{crlf}"
                     f"Content-Type: image/png{crlf}{crlf}")
            casti.append(hlava.encode() + bytes(v) + crlf.encode())
        else:
            text = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            hlava = f"--{hranica}{crlf}Content-Disposition: form-data; name=\"{k}\"{crlf}{crlf}"
            casti.append(hlava.encode() + text.encode("utf-8") + crlf.encode())
    return b"".join(casti) + f"--{hranica}--{crlf}".encode(), f"multipart/form-data; boundary={hranica}"


class TelegramError(Exception):
    def __init__(self, message: str, retry_after: float | None = None, code: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.code = code

    @property
    def permanent(self) -> bool:
        """400 (zlá správa) a 403 (bot vyhodený z chatu) sa opakovaním nezmenia — na rozdiel od siete, 429 a 5xx."""
        return self.code in (400, 403)


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
        if any(isinstance(v, (bytes, bytearray)) for v in payload.values()):
            data, ctype = _multipart(payload)
        else:
            data, ctype = json.dumps(payload).encode("utf-8"), "application/json"
        req = urllib.request.Request(f"{API}/bot{self.token}/{method}", data=data,
                                     headers={"Content-Type": ctype}, method="POST")
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
        raise TelegramError(text, float(retry) if retry else None, code if isinstance(code, int) else None)

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

    def send_photo(self, chat_id: int, png: bytes, caption: str = "", buttons: list[list[dict]] | None = None) -> Any:
        """Obrázok (PNG) s popisom v HTML; ten istý odstup v chate ako `send`."""
        payload: dict[str, Any] = {"chat_id": chat_id, "photo": bytes(png), "caption": caption[:1024], "parse_mode": "HTML"}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        with self._lock:
            cakaj = self._last_send.get(chat_id, -1e9) + self.min_interval - self.clock()
            if cakaj > 0:
                self.sleep(cakaj)
            try:
                return self.call("sendPhoto", payload, timeout=60.0)
            finally:
                self._last_send[chat_id] = self.clock()

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

    def pin(self, chat_id: int, message_id: int) -> None:
        self.call("pinChatMessage", {"chat_id": chat_id, "message_id": message_id, "disable_notification": True})

    def unpin(self, chat_id: int, message_id: int) -> None:
        self.call("unpinChatMessage", {"chat_id": chat_id, "message_id": message_id})

    def set_commands(self, commands: list[tuple[str, str]]) -> None:
        """Menu „/“ v Telegrame (zoznam príkazov s popisom)."""
        self.call("setMyCommands", {"commands": [{"command": c, "description": d} for c, d in commands]})
