"""Pluginy hubu (docs/HUB.md, „Pluginy“): vlastný kód, ktorý beží v procese hubu.

Plugin = balík `tester/hub/plugins/<meno>/`, ktorý vystaví `PLUGIN = <podtrieda HubPlugin>`.
`PluginHost` ich pri `hub serve` nájde sám, každému dá `PluginContext` a vlastné vlákno a volá
`tick()` každých `interval` sekúnd, kým nemá v `hub_data/plugins/<meno>/config.json`
`"enabled": false` (preverí sa pri každom ticku, reštart netreba). Výnimka v pluginu hub nezhodí —
zapíše sa do stavu a strážca (`watchdog`) ju ohlási. Hub nepozná plugin menom.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from .base import HubNotifier, HubPlugin, NotifyError, PluginContext

__all__ = ["HubPlugin", "PluginContext", "HubNotifier", "NotifyError", "PluginHost", "discover"]

log = logging.getLogger(__name__)


def discover() -> list[str]:
    """Mená balíkov v `tester/hub/plugins/` (bez `_…`), v abecednom poradí."""
    return sorted(m.name for m in pkgutil.iter_modules(__path__) if m.ispkg and not m.name.startswith("_"))


def _load_class(name: str) -> type[HubPlugin]:
    mod = importlib.import_module(f"{__name__}.{name}")
    cls = getattr(mod, "PLUGIN", None)
    if not (isinstance(cls, type) and issubclass(cls, HubPlugin)):
        raise TypeError(f"{name}: balík nevystavuje PLUGIN = podtrieda HubPlugin")
    return cls


class _Slot:
    """Jeden plugin v hoste: inštancia a záznam o jeho behu."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.plugin: HubPlugin | None = None
        self.ctx: PluginContext | None = None
        self.load_error = ""
        self.thread: threading.Thread | None = None
        self.ticks = 0
        self.last_tick = 0.0
        self.last_ok = 0.0
        self.last_error = ""
        self.error_since = 0.0
        self.errors = 0          # po sebe idúce
        self.tick_started = 0.0  # > 0 = tick práve beží


class PluginHost:
    def __init__(self, root: Path, hub: Any, notifier: Any, *, names: list[str] | None = None,
                 classes: dict[str, type[HubPlugin]] | None = None, clock: Callable[[], float] = time.time) -> None:
        """`root` = `hub_data/plugins`; `classes` podstrčí pluginy (testy) namiesto hľadania v balíku."""
        self.root = Path(root)
        self.hub = hub
        self.notifier = notifier
        self.clock = clock
        self.started = clock()
        self._stop = threading.Event()
        self.slots: dict[str, _Slot] = {}
        for name in (sorted(classes) if classes is not None else (names if names is not None else discover())):
            slot = _Slot(name)
            self.slots[name] = slot
            try:
                cls = classes[name] if classes is not None else _load_class(name)
                p = cls()
                p.name = name
                p.title = p.title or name
                ctx = PluginContext(name, self.root, hub, notifier, host=self, clock=clock)
                p.setup(ctx)
                slot.plugin, slot.ctx = p, ctx
            except Exception as exc:  # noqa: BLE001 - zlý plugin nesmie zhodiť hub
                slot.load_error = f"{type(exc).__name__}: {exc}"
                log.warning("plugin %s sa nenačítal: %s", name, slot.load_error)

    def enabled(self, name: str) -> bool:
        s = self.slots[name]
        if s.plugin is None or s.ctx is None:
            return False
        return bool(s.ctx.config().get("enabled", s.plugin.default_enabled))

    def run_once(self, name: str) -> bool:
        """Jeden tick s evidenciou; vráti, či prebehol bez chyby."""
        s = self.slots[name]
        if s.plugin is None:
            return False
        now = self.clock()
        s.tick_started = now
        try:
            s.plugin.tick()
        except Exception as exc:  # noqa: BLE001
            s.last_error = f"{type(exc).__name__}: {exc}"
            s.errors += 1
            if s.errors == 1:
                s.error_since = now
                log.warning("plugin %s: %s\n%s", name, s.last_error, traceback.format_exc(limit=4))
            return False
        finally:
            s.ticks += 1
            s.last_tick = self.clock()
            s.tick_started = 0.0
        s.last_ok = s.last_tick
        s.errors, s.error_since = 0, 0.0
        return True

    def start(self) -> None:
        for name, s in self.slots.items():
            if s.plugin is None:
                continue

            def loop(name: str = name, s: _Slot = s) -> None:
                while not self._stop.is_set():
                    try:
                        if self.enabled(name):
                            self.run_once(name)
                    except Exception as exc:  # noqa: BLE001 - aj config/enabled
                        s.last_error = f"{type(exc).__name__}: {exc}"
                    if self._stop.wait(max(1.0, float(s.plugin.interval))):
                        break

            s.thread = threading.Thread(target=loop, name=f"hub-plugin-{name}", daemon=True)
            s.thread.start()

    def stop(self) -> None:
        self._stop.set()
        for s in self.slots.values():
            if s.plugin is not None:
                try:
                    s.plugin.teardown()
                except Exception as exc:  # noqa: BLE001
                    log.warning("plugin %s teardown: %s", s.name, exc)

    def status(self) -> list[dict[str, Any]]:
        out = []
        for name, s in self.slots.items():
            detail: dict[str, Any] = {}
            if s.plugin is not None:
                try:
                    detail = dict(s.plugin.status() or {})
                except Exception as exc:  # noqa: BLE001
                    detail = {"problem": f"status: {type(exc).__name__}: {exc}"}
            out.append({
                "name": name, "title": s.plugin.title if s.plugin else name,
                "enabled": self.enabled(name) if s.plugin else False,
                "running": bool(s.thread and s.thread.is_alive()),
                "load_error": s.load_error, "ticks": s.ticks, "last_tick": s.last_tick, "last_ok": s.last_ok,
                "last_error": s.last_error, "errors": s.errors, "error_since": s.error_since,
                "tick_started": s.tick_started, "max_tick": s.plugin.max_tick if s.plugin else 0.0,
                "interval": s.plugin.interval if s.plugin else 0.0,
                "problem": detail.pop("problem", None), "detail": detail,
            })
        return out

    def views(self) -> list[dict[str, str]]:
        """Pohľady zapnutých pluginov pre Telegram: `[{plugin, view, label}]`."""
        out = []
        for name, s in self.slots.items():
            if s.plugin is None or not self.enabled(name):
                continue
            try:
                ponuka = dict(s.plugin.views() or {})
            except Exception as exc:  # noqa: BLE001
                log.warning("plugin %s views: %s", name, exc)
                continue
            out += [{"plugin": name, "view": v, "label": str(label)} for v, label in ponuka.items()]
        return out

    def view(self, plugin: str, name: str) -> str:
        """Text pohľadu; neznámy plugin či pohľad = `KeyError`."""
        s = self.slots.get(plugin)
        if s is None or s.plugin is None or not self.enabled(plugin) or name not in (s.plugin.views() or {}):
            raise KeyError(f"{plugin}/{name}")
        return str(s.plugin.view(name))

    def get(self, name: str) -> HubPlugin | None:
        s = self.slots.get(name)
        return s.plugin if s else None
