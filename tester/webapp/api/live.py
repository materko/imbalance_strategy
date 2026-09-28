"""Live telemetria zo spustených stratégií (docs/LIVE.md) — karta **Live** (`/api/live*`).

Webapp si udalosti **zrkadlí** do vlastného sqlite (`tester/live/mirror.sqlite`, `LiveStore`)
z dvoch zdrojov a stránka číta len zrkadlo:

* z hubu (`GET /api/live/export?after=<kurzor>`), keď má klon `tester/agent.json` — kurzor je
  rowid hubu a drží sa v `tester/live/mirror_cursor.json`; hub dole = ukazuje sa, čo je;
* z lokálneho spoolu platforiem (`tradebot.live.spool`), keď webapp beží na obchodnom PC —
  vlastný kurzor `tester/live/cursor_webapp.json`, funguje aj bez hubu.

`LiveMirror` je vlákno, ktoré to robí každých 5 s; štartuje ho `__main__` (ako agenta hubu),
takže testy s `TestClient` ho nespúšťajú a zrkadlo sa otvára až pri prvom použití.
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from tradebot.core.paths import LIVE_CURSOR_WEBAPP, LIVE_MIRROR, LIVE_MIRROR_CURSOR
from tradebot.live.store import LiveStore

from .context import AppContext

__all__ = ["LiveMirror", "build"]

#: Koľko riadkov naraz pýta zrkadlo od hubu (strop hubu je tiež 5000).
EXPORT_LIMIT = 5000
#: Koľko dávok lokálneho spoolu najviac za jeden tik — nech dobiehanie neblokuje hub.
LOCAL_BATCHES_PER_TICK = 20


def _short(exc: BaseException, limit: int = 200) -> str:
    """Chyba na jeden riadok stavu: HTML telo od proxy (503) sa zredukuje na text a skráti."""
    text = re.sub(r"<[^>]+>", " ", str(exc))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _default_hub() -> tuple[Any, Any] | None:
    """`(cfg, http)` hubu z `tester/agent.json`, alebo None (nenastavený / neposiela)."""
    from ...hub import config as hub_config
    from ...hub.client import HubHttp

    cfg = hub_config.load()
    if cfg is None or not cfg.send:
        return None
    return cfg, HubHttp(cfg.hub_url, cfg.token, timeout=15.0)


def _default_reader(cursor_path: Path) -> Any | None:
    """`SpoolReader` nad korenmi spoolu tohto stroja, alebo None (žiadny koreň, modul chýba)."""
    try:
        from tradebot.live import spool
    except ImportError:
        return None
    roots = spool.default_roots()
    if not roots:
        return None
    return spool.SpoolReader(roots, cursor_path)


class LiveMirror:
    """Zrkadlo udalostí: hub → store, lokálny spool → store. Bez vlákna sa dá volať `tick()`."""

    def __init__(self, mirror_path: Path = LIVE_MIRROR, cursor_path: Path = LIVE_MIRROR_CURSOR, *,
                 local_cursor: Path = LIVE_CURSOR_WEBAPP,
                 hub_factory: Callable[[], tuple[Any, Any] | None] = _default_hub,
                 reader_factory: Callable[[Path], Any | None] = _default_reader,
                 interval: float = 5.0, clock: Callable[[], float] = time.time) -> None:
        self.mirror_path = Path(mirror_path)
        self.cursor_path = Path(cursor_path)
        self.local_cursor = Path(local_cursor)
        self.hub_factory = hub_factory
        self.reader_factory = reader_factory
        self.interval = interval
        self.clock = clock
        self._store: LiveStore | None = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._reader: Any | None = None
        self.hub_url: str | None = None
        self.hub_cursor = 0
        self.local_agent = "local"
        self.local_roots: list[str] = []
        self.last_ok: float | None = None
        self.last_error: str | None = None
        self.ticks = 0
        self.ingested = 0

    # -- store a kurzor ------------------------------------------------------- #

    @property
    def store(self) -> LiveStore:
        """Zrkadlo sa otvára až pri prvom použití — zostavenie aplikácie nič na disk nepíše."""
        with self._lock:
            if self._store is None:
                self._store = LiveStore(self.mirror_path, clock=self.clock)
            return self._store

    def _load_cursor(self, hub_url: str) -> int:
        try:
            data = json.loads(self.cursor_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        if not isinstance(data, dict) or data.get("hub_url") != hub_url:
            return 0
        try:
            return max(0, int(data.get("cursor") or 0))
        except (TypeError, ValueError):
            return 0

    def _save_cursor(self) -> None:
        self.cursor_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cursor_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"hub_url": self.hub_url, "cursor": self.hub_cursor}), encoding="utf-8")
        tmp.replace(self.cursor_path)

    # -- zdroje ---------------------------------------------------------------- #

    def pull_hub(self, http: Any, *, limit: int = EXPORT_LIMIT) -> int:
        """Stiahne z hubu všetko za kurzorom (po stránkach) a uloží; vráti počet nových udalostí.

        Riadky sa zoskupia podľa (agent, inštancia, session) — `ingest` je idempotentný, takže
        opakovaná stránka (pád medzi uložením a zápisom kurzora) nič nezdvojí."""
        total = 0
        while True:
            rows = http.get(f"/api/live/export?after={int(self.hub_cursor)}&limit={int(limit)}")
            if not isinstance(rows, list) or not rows:
                break
            groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
            for r in rows:
                key = (str(r.get("agent") or ""), str(r["instance"]), str(r["session"]))
                groups.setdefault(key, []).append(r["event"])
            for (agent, instance, session), events in groups.items():
                total += self.store.ingest(agent, instance, session, events)
            self.hub_cursor = max(self.hub_cursor, max(int(r["id"]) for r in rows))
            self._save_cursor()
            if len(rows) < limit:
                break
        return total

    def pull_local(self, reader: Any, agent: str) -> int:
        """Prečíta lokálny spool od kurzora webapp, uloží a kurzor potvrdí až po zápise."""
        total = 0
        for _ in range(LOCAL_BATCHES_PER_TICK):
            batches = reader.read(max_events=500)
            if not batches:
                break
            for batch in batches:
                total += self.store.ingest(agent, batch.instance, batch.session, list(batch.events))
                reader.commit(batch)
        return total

    def tick(self) -> None:
        """Jeden prechod oboma zdrojmi. Chyba sa zapíše do `last_error` a ďalší tik ide znova."""
        self.ticks += 1
        errors: list[str] = []
        agent_name = "local"
        try:
            hub = self.hub_factory()
            if hub is not None:
                cfg, http = hub
                agent_name = str(getattr(cfg, "name", "") or "local")
                url = str(getattr(cfg, "hub_url", "") or "")
                if url != self.hub_url:
                    self.hub_url = url
                    self.hub_cursor = self._load_cursor(url)
                self.ingested += self.pull_hub(http)
            else:
                self.hub_url = None
        except Exception as exc:  # noqa: BLE001 - hub mimo nesmie zhodiť zrkadlo
            errors.append(f"hub: {type(exc).__name__}: {_short(exc)}")
        self.local_agent = agent_name
        try:
            if self._reader is None:
                self._reader = self.reader_factory(self.local_cursor)
                if self._reader is not None:
                    self.local_roots = [str(r) for r in (getattr(self._reader, "roots", None) or [])]
            if self._reader is not None:
                self.ingested += self.pull_local(self._reader, agent_name)
        except Exception as exc:  # noqa: BLE001 - rozbitý spool takisto nie
            errors.append(f"spool: {type(exc).__name__}: {_short(exc)}")
        if errors:
            self.last_error = "; ".join(errors)
        else:
            self.last_error = None
            self.last_ok = self.clock()

    # -- vlákno ---------------------------------------------------------------- #

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="live-mirror", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        t = self._thread
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(timeout)
        self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - vlákno nesmie umrieť
                self.last_error = f"{type(exc).__name__}: {exc}"
            self._stop.wait(self.interval)

    def status(self) -> dict[str, Any]:
        return {
            "hub_url": self.hub_url,
            "hub_cursor": int(self.hub_cursor),
            "last_ok": self.last_ok,
            "last_error": self.last_error,
            "local_roots": list(self.local_roots),
            "local_agent": self.local_agent,
            "running": self.running,
            "ticks": self.ticks,
            "ingested": self.ingested,
        }


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    app = ctx.app

    mirror = LiveMirror(LIVE_MIRROR, LIVE_MIRROR_CURSOR, local_cursor=LIVE_CURSOR_WEBAPP)
    app.state.live_mirror = mirror

    def start_live_mirror() -> LiveMirror:
        """Štart zrkadla v tomto procese — volá `__main__` pri štarte webapp (ako agenta hubu)."""
        mirror.start()
        return mirror

    app.state.start_live_mirror = start_live_mirror

    @router.get("/api/live")
    def live_overview():
        """Inštancie v zrkadle a stav zrkadla (hub, kurzor, lokálny spool, posledná chyba)."""
        return {"instances": mirror.store.instances(), "mirror": mirror.status(),
                "now": int(mirror.clock() * 1000)}

    @router.get("/api/live/{instance}/sessions")
    def live_sessions(instance: str):
        """Behy (sessions) inštancie zo zrkadla, najnovší prvý — výber „Beh“ v detaile."""
        if mirror.store.instance(instance) is None:
            raise HTTPException(404, f"inštancia {instance!r} v zrkadle nie je")
        return mirror.store.sessions(instance)

    @router.get("/api/live/{instance}/snapshot")
    def live_snapshot(instance: str, bars: int | None = Query(None, ge=1, le=5000), session: str = ""):
        """Bez `session` posledných 500 barov naprieč behmi; so `session` celý ten beh (do 5000 barov)."""
        snap = mirror.store.snapshot(instance, bars=bars, session=session or None)
        if snap["instance"] is None:
            raise HTTPException(404, f"inštancia {instance!r} v zrkadle nie je")
        return snap

    @router.get("/api/live/{instance}/events")
    def live_events(instance: str, after: int = 0, kinds: str = "", limit: int = Query(1000, ge=1, le=10000),
                    session: str = ""):
        druhy = [k.strip() for k in kinds.split(",") if k.strip()] or None
        return mirror.store.events(instance, after=after, kinds=druhy, limit=limit, session=session or None)

    return router
