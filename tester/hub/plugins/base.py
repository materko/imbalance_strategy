"""Kontrakt pluginu hubu (docs/HUB.md, „Pluginy“): čo plugin dostane (`PluginContext`) a čo dodá (`HubPlugin`).

Plugin nevidí nič iné ako svoj kontext: vlastný adresár `hub_data/plugins/<meno>/` (config, stav,
zásoba), Telegram hubu cez `notify` (token nikdy), log, log udalostí hubu a hub len na čítanie.
Vlákno, interval a zachytenie výnimiek drží `PluginHost` — plugin píše len `tick()`.
"""

from __future__ import annotations

import html
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable

from tradebot.live.telegram import TelegramBot, TelegramError, load_config

__all__ = ["HubPlugin", "PluginContext", "HubNotifier", "NotifyError", "write_json", "read_json"]

#: Odoslanie zlyhalo (Telegram dole, 429 …) alebo Telegram na hube nie je nastavený.
NotifyError = TelegramError


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any) -> None:
    """Atomický zápis (tmp + replace) — výpadok uprostred nenechá rozbitý stav."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


class HubNotifier:
    """Telegram hubu (`HUB_TELEGRAM_CONFIG`) pre všetky pluginy: config sa načíta znova pri zmene súboru,
    pred text ide `[label]`. Bez configu `enabled` = False a `send` hodí `NotifyError`."""

    def __init__(self, path: Path, *, bot_factory: Callable[[str], Any] = TelegramBot) -> None:
        self.path = Path(path)
        self.bot_factory = bot_factory
        self._mtime: float | None = -1.0
        self.cfg = None
        self.bot = None

    def _reload(self) -> None:
        try:
            mtime: float | None = self.path.stat().st_mtime
        except OSError:
            mtime = None
        if mtime == self._mtime:
            return
        self._mtime = mtime
        cfg = load_config(self.path)   # aj env TRADEBOT_TELEGRAM_TOKEN / _CHATS
        if cfg is None:
            self.cfg = self.bot = None
        elif self.cfg is None or cfg.token != self.cfg.token or self.bot is None:
            self.cfg, self.bot = cfg, self.bot_factory(cfg.token)
        else:
            self.cfg = cfg

    @property
    def enabled(self) -> bool:
        self._reload()
        return self.cfg is not None

    @property
    def chats(self) -> list[int]:
        self._reload()
        return list(self.cfg.chats) if self.cfg else []

    def send(self, text: str, *, html_mode: bool = True, chats: list[int] | None = None) -> None:
        self._reload()
        if self.cfg is None or self.bot is None:
            raise NotifyError("Telegram na hube nie je nastavený (hub_data/telegram.json)")
        if self.cfg.label:
            text = f"[{html.escape(self.cfg.label) if html_mode else self.cfg.label}] {text}"
        for chat in chats or self.cfg.chats:
            self.bot.send(chat, text, html=html_mode)


class PluginContext:
    def __init__(self, name: str, root: Path, hub: Any, notifier: Any, *, host: Any = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.name = name
        self.dir = Path(root) / name
        self.hub = hub
        self.notifier = notifier
        self.host = host
        self.clock = clock
        self.log = logging.getLogger(f"tester.hub.plugins.{name}")
        self._cfg: dict[str, Any] = {}
        self._cfg_mtime: float | None = -1.0

    @property
    def config_path(self) -> Path:
        return self.dir / "config.json"

    def config(self) -> dict[str, Any]:
        """`config.json` pluginu; znova pri zmene súboru, chýba alebo je rozbitý = `{}`."""
        try:
            mtime: float | None = self.config_path.stat().st_mtime
        except OSError:
            mtime = None
        if mtime != self._cfg_mtime:
            self._cfg_mtime = mtime
            raw = read_json(self.config_path, {}) if mtime is not None else {}
            if not isinstance(raw, dict):
                self.log.warning("%s: config nie je objekt", self.config_path)
                raw = {}
            self._cfg = raw
        return self._cfg

    def path(self, name: str) -> Path:
        return self.dir / name

    @property
    def can_notify(self) -> bool:
        return bool(self.notifier is not None and self.notifier.enabled)

    def notify(self, text: str, *, html: bool = True, chats: list[int] | None = None) -> None:
        """Do Telegramu hubu; zlyhanie = `NotifyError` (plugin si nechá zmenu na ďalší tick)."""
        if self.notifier is None:
            raise NotifyError("Telegram na hube nie je nastavený")
        self.notifier.send(text, html_mode=html, chats=chats)

    def event(self, event: str, **fields: Any) -> None:
        """Do logu udalostí hubu (`python -m tester.hub events`) ako `plugin_<event>`."""
        log = getattr(self.hub, "log", None)
        if callable(log):
            log(f"plugin_{event}", plugin=self.name, **fields)

    def plugins(self) -> list[dict[str, Any]]:
        """Stav všetkých pluginov (pre strážcu)."""
        return self.host.status() if self.host is not None else []


class HubPlugin:
    """Základ pluginu. Balík `tester/hub/plugins/<meno>/` vystaví `PLUGIN = <trieda>`."""

    #: zhodné s menom balíka (doplní host)
    name = ""
    title = ""
    #: sekundy medzi tickmi
    interval = 20.0
    #: tick dlhší ako toto = plugin visí (strážca to ohlási)
    max_tick = 600.0
    #: bez `enabled` v configu
    default_enabled = True

    def setup(self, ctx: PluginContext) -> None:
        self.ctx = ctx

    def tick(self) -> None:
        """Jedno kolo práce; výnimka = chyba pluginu (host ju zachytí a zapíše do stavu)."""

    def status(self) -> dict[str, Any]:
        """Čo ukázať v `hub plugins`; `problem` (text) = strážca ho ohlási, `None` = v poriadku."""
        return {}

    def views(self) -> dict[str, str]:
        """Pohľady pre Telegram agenta: meno → text gombíka (napr. `{"upcoming": "📅 Udalosti"}`). Agent si gombíky
        poskladá z `GET /api/plugins/views`, takže ani on plugin nepozná menom."""
        return {}

    def view(self, name: str) -> str:
        """Pohľad ako HTML pre Telegram (`<b>`, `<i>`, `<code>`; volajúci escapuje). Neznámy = `KeyError`."""
        raise KeyError(name)

    def teardown(self) -> None:
        pass

    def cli(self, argv: list[str]) -> int:
        """`python -m tester.hub plugin <meno> …` na stroji hubu."""
        print(f"plugin {self.name} nemá príkazy")
        return 0
