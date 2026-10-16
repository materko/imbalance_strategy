"""Strážca hubu pre Telegram (docs/LIVE.md, „Telegram“): ohlási, keď stroj s aktívnym nasadením
prestane posielať heartbeat, a keď sa vráti.

To je jediná správa, ktorú agent ani adaptér o sebe poslať nevedia — spadnutý agent, vypnutý stroj
alebo výpadok internetu doma vidno len zvonka. Hub **len posiela** (`sendMessage`); príkazy prijíma
agent, lebo `getUpdates` smie na bote volať jediný proces. Config `HUB_TELEGRAM_CONFIG` má ten istý
tvar ako na agentovi (`commands` sa ignoruje).

Offline = `now - last_seen > agent_timeout + OFFLINE_GRACE` a hub beží aspoň toľko (po reštarte hubu
sú všetci agenti chvíľu „offline“, kým sa neohlásia). Čo naposledy ohlásil, si pamätá v
`HUB_TELEGRAM_STATE`, aby po reštarte nehlásil to isté znova.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from tradebot.live.telegram import TelegramBot, TelegramConfig, TelegramError

__all__ = ["HubTelegramWatch", "OFFLINE_GRACE", "CHECK_SECONDS"]

log = logging.getLogger(__name__)

#: Navyše k `agent_timeout`, kým sa stroj ohlási ako nedostupný (krátky výpadok siete nespamuje).
OFFLINE_GRACE = 120.0
CHECK_SECONDS = 20.0


class HubTelegramWatch:
    def __init__(self, state: Any, cfg: TelegramConfig, state_path: Path, *, bot: TelegramBot | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.hub = state
        self.cfg = cfg
        self.bot = bot or TelegramBot(cfg.token)
        self.state_path = Path(state_path)
        self.clock = clock
        self.started = clock()
        self.reported: dict[str, bool] = {}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.reported = {str(k): bool(v) for k, v in (raw.get("online") or {}).items()}
        except (OSError, ValueError, AttributeError):
            pass
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_name(self.state_path.name + ".tmp")
        tmp.write_text(json.dumps({"online": self.reported}, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def _send(self, text: str) -> None:
        if self.cfg.label:
            text = f"[{self.cfg.label}] {text}"
        for chat in self.cfg.chats:
            self.bot.send(chat, text)

    def check(self) -> list[str]:
        """Jedno kolo: stav strojov s aktívnym nasadením → správy o zmene. Vráti odoslané texty;
        Telegram dole = stav sa neuloží a zmena sa ohlási v ďalšom kole."""
        if self.hub.deploy is None:
            return []
        now = self.clock()
        limit = float(self.hub.agent_timeout) + OFFLINE_GRACE
        if now - self.started < limit:
            return []   # po štarte hubu sa agenti ešte neohlásili
        with self.hub._lock:
            agents = {n: dict(a) for n, a in self.hub.agents.items()}
        spravy: list[tuple[str, bool, str]] = []
        zmena = False
        for name in self.hub.deploy.active_agents():
            a = agents.get(name) or {}
            ticho = now - float(a.get("last_seen") or 0)
            online = ticho <= limit
            predtym = self.reported.get(name)
            if predtym is None:
                if not online:   # prvé pozorovanie: hlásiť len problém
                    spravy.append((name, online, f"🔴 stroj {name} sa neozval {int(ticho // 60)} min — nasadenia na ňom "
                                                 f"bežia ďalej, ale bez dohľadu a bez príkazov z webapp"))
                else:
                    self.reported[name] = True
                    zmena = True
                continue
            if predtym and not online:
                spravy.append((name, online, f"🔴 stroj {name} sa neozval {int(ticho // 60)} min — nasadenia na ňom "
                                             f"bežia ďalej, ale bez dohľadu a bez príkazov z webapp"))
            elif not predtym and online:
                spravy.append((name, online, f"🟢 stroj {name} sa znova hlási"))
        odoslane = []
        for name, online, text in spravy:
            try:
                self._send(text)
            except TelegramError as exc:
                log.warning("hub telegram: %s", exc)
                break
            self.reported[name] = online
            odoslane.append(text)
            zmena = True
        if zmena:
            self._save()
        return odoslane

    def start(self) -> None:
        def loop() -> None:
            while not self._stop.wait(CHECK_SECONDS):
                try:
                    self.check()
                except Exception as exc:  # noqa: BLE001 - strážca nesmie umrieť
                    log.warning("hub telegram: %s: %s", type(exc).__name__, exc)

        self._thread = threading.Thread(target=loop, name="hub-telegram", daemon=True)
        self._thread.start()
        log.info("hub: telegram strážca zapnutý (%d chat(y))", len(self.cfg.chats))

    def stop(self) -> None:
        self._stop.set()
