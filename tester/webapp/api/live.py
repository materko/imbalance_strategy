"""Live telemetria zo spustených stratégií (docs/LIVE.md) — karta **Live** (`/api/live*`).

Webapp si udalosti **zrkadlí** do vlastného sqlite (`tester/live/mirror.sqlite`, `LiveStore`)
z dvoch zdrojov a stránka číta len zrkadlo:

* z hubu cez `Transport.pull_export` (`tradebot.live.transport`; dnes HTTP
  `GET /api/live/export?after=<kurzor>`), keď má klon `tester/agent.json` — kurzor je rowid
  hubu a drží sa v `tester/live/mirror_cursor.json`; hub dole = ukazuje sa, čo je;
* z lokálneho spoolu platforiem (`tradebot.live.spool`), keď webapp beží na obchodnom PC —
  vlastný kurzor `tester/live/cursor_webapp.json`, funguje aj bez hubu.

`LiveMirror` je vlákno, ktoré to robí každé 2 s (plná stránka z hubu = hneď ďalšia); štartuje
ho `__main__` (ako agenta hubu), takže testy s `TestClient` ho nespúšťajú a zrkadlo sa otvára
až pri prvom použití. Každé uložené nové riadky zdvihnú `version` zrkadla a zobudia
čakajúcich (`wait_for_change`) — na tom stojí `GET /api/live/stream` (SSE): stránka nič
nepolluje, server jej pošle `instances` (zoznam + stav zrkadla) a `events` (nové riadky
inštancie) hneď, ako prídu; každých 15 s ide komentár ako keepalive.

Fáza 2b (účty a nasadenia, sekcie **Účty** a **Nasadenia** na karte): webapp nič nezrkadlí,
len **preposiela** na hub — čítanie s tokenom agenta (`/api/live/accounts`, `/deployments`,
`/audit`, `/agents`), mutácie s hlavným tokenom (`admin_token` v `tester/agent.json` alebo
`TRADEBOT_HUB_ADMIN_TOKEN`; bez neho 403 a karta je len na čítanie). Heslo účtu ide na hub
raz v tele požiadavky a nikde tu sa neukladá ani neloguje. Config nasadenia sa z profilu
skladá tu (webapp má aj vlastné profily testera) a na hub ide už hotový.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from tradebot.core.config import ConfigError
from tradebot.core.paths import LIVE_CURSOR_WEBAPP, LIVE_MIRROR, LIVE_MIRROR_CURSOR
from tradebot.live.store import LiveStore
from tradebot.live.transport import as_transport
from tradebot.strategies import STRATEGIES, canonical_key

from ..runner import default_params, list_profiles, profile_titles
from .common import clean_user
from .context import AppContext

__all__ = ["LiveMirror", "build", "sse_event", "stream_messages", "MIRROR_INTERVAL"]

#: Koľko riadkov naraz pýta zrkadlo od hubu (strop hubu je tiež 5000).
EXPORT_LIMIT = 5000
#: Koľko dávok lokálneho spoolu najviac za jeden tik — nech dobiehanie neblokuje hub.
LOCAL_BATCHES_PER_TICK = 20
#: Interval zrkadla (hub + lokálny spool). 2 s: hub sám dostáva dávky do ~1 s od baru, takže
#: koniec-koniec je bar → stránka ≈ 2–4 s; plná stránka z hubu sa dočíta hneď (bez čakania).
MIRROR_INTERVAL = 2.0
#: SSE: komentár každých toľko sekúnd, nech proxy a prehliadač spojenie nezavrú.
SSE_KEEPALIVE = 15.0
#: SSE: ako dlho generátor čaká na zmenu zrkadla, než skontroluje odpojenie klienta.
SSE_WAIT = 1.0


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
                 interval: float = MIRROR_INTERVAL, clock: Callable[[], float] = time.time) -> None:
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
        #: Rastie s každým tikom, ktorý niečo uložil; `wait_for_change` na ňom čaká (SSE).
        self.version = 0
        self._changed = threading.Condition()

    # -- poslucháči (SSE) ------------------------------------------------------ #

    def _bump(self, n: int) -> None:
        if n <= 0:
            return
        with self._changed:
            self.version += 1
            self._changed.notify_all()

    def wait_for_change(self, since: int, timeout: float | None = None) -> int:
        """Čaká, kým `version` prerastie `since` (alebo uplynie `timeout`); vráti aktuálnu."""
        with self._changed:
            if self.version <= since:
                self._changed.wait(timeout)
            return self.version

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

    def pull_hub(self, transport: Any, *, limit: int = EXPORT_LIMIT) -> int:
        """Stiahne z hubu všetko za kurzorom (po stránkach; plná stránka = hneď ďalšia) a uloží;
        vráti počet nových udalostí. `transport` je `Transport` (alebo HTTP klient, ktorý sa zabalí).

        Riadky sa zoskupia podľa (agent, inštancia, session) — `ingest` je idempotentný, takže
        opakovaná stránka (pád medzi uložením a zápisom kurzora) nič nezdvojí."""
        transport = as_transport(transport)
        total = 0
        while True:
            rows = transport.pull_export(int(self.hub_cursor), int(limit))
            if not isinstance(rows, list) or not rows:
                break
            groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
            for r in rows:
                key = (str(r.get("agent") or ""), str(r["instance"]), str(r["session"]))
                groups.setdefault(key, []).append(r["event"])
            nove = 0
            for (agent, instance, session), events in groups.items():
                nove += self.store.ingest(agent, instance, session, events)
            self.hub_cursor = max(self.hub_cursor, max(int(r["id"]) for r in rows))
            self._save_cursor()
            self._bump(nove)
            total += nove
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
            nove = 0
            for batch in batches:
                nove += self.store.ingest(agent, batch.instance, batch.session, list(batch.events))
                reader.commit(batch)
            self._bump(nove)
            total += nove
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
            "version": self.version,
            "interval": self.interval,
        }


# --------------------------------------------------------------------------- #
# SSE: `GET /api/live/stream`
# --------------------------------------------------------------------------- #


def sse_event(data: Any, *, event: str | None = None) -> str:
    """Jedna správa SSE: `event:` (voliteľne) + `data:` s JSON na jednom riadku + prázdny riadok."""
    telo = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    hlava = f"event: {event}\n" if event else ""
    return f"{hlava}data: {telo}\n\n"


def stream_messages(mirror: LiveMirror, *, after: int, deploy: Callable[[], Any] | None = None,
                    limit: int = EXPORT_LIMIT) -> Iterator[dict[str, Any]]:
    """Správy pre klienta po zmene zrkadla: nové riadky od `after` (rowid zrkadla) zoskupené
    podľa inštancie ako `{"type": "events", "instance", "rows": [...]}` (riadky ako
    `LiveStore.events`: `id`, `session`, `seq`, `event`) a na záver jedno
    `{"type": "instances", "instances", "mirror", "now", "deploy"}` — to isté, čo `GET /api/live`."""
    store = mirror.store
    kurzor = int(after)
    while True:
        rows = store.export(after=kurzor, limit=limit)
        if not rows:
            break
        po_instancii: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            po_instancii.setdefault(str(r["instance"]), []).append(
                {"id": r["id"], "session": r["session"], "seq": r["seq"], "event": r["event"]})
        for instance, riadky in po_instancii.items():
            yield {"type": "events", "instance": instance, "rows": riadky}
        kurzor = max(int(r["id"]) for r in rows)
        if len(rows) < limit:
            break
    yield {"type": "instances", "instances": store.instances(), "mirror": mirror.status(),
           "now": int(mirror.clock() * 1000), "deploy": deploy() if deploy else None, "cursor": kurzor}


class LiveAccountRequest(BaseModel):
    """Účet do hubu; `password` sa preposiela raz a nikde vo webapp neostáva."""
    id: str | None = None
    agent: str | None = None
    platform: str | None = None
    label: str | None = None
    login: str | None = None
    server: str | None = None
    terminal: str | None = None
    portable: bool | None = None
    password: str | None = None
    user: str | None = None


class LiveDeploymentRequest(BaseModel):
    account: str
    strategy: str
    symbol: str
    tf: int
    profile: str = ""
    config: dict[str, Any] | None = None
    mode: str = "enabled"
    user: str | None = None


class LiveDeploymentPatch(BaseModel):
    mode: str | None = None
    profile: str | None = None
    config: dict[str, Any] | None = None
    active: bool | None = None
    user: str | None = None


class LiveCodeUpdateRequest(BaseModel):
    """„Aktualizovať kód na stroji“ (fáza 2c): cieľový commit (bez neho commit tejto webapp) a `force`."""
    version: str | None = None
    force: bool = False
    user: str | None = None


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
        """Inštancie v zrkadle, stav zrkadla (hub, kurzor, lokálny spool, posledná chyba) a či
        táto webapp smie nasadenia aj meniť (`deploy.admin` = má hlavný token hubu).
        `cursor` je rowid zrkadla — odtiaľ pokračuje `/api/live/stream?after=`."""
        return {"instances": mirror.store.instances(), "mirror": mirror.status(),
                "now": int(mirror.clock() * 1000), "deploy": _deploy_state(),
                "cursor": mirror.store.cursor()}

    @router.get("/api/live/stream")
    async def live_stream(request: Request, after: int = Query(-1, ge=-1)):
        """SSE (`text/event-stream`): po každej zmene zrkadla pošle nové riadky (`events`, po
        inštanciách) a zoznam inštancií so stavom (`instances`); bez zmeny každých 15 s komentár.
        `after` = rowid zrkadla, od ktorého klient riadky ešte nemá (-1 = len od teraz)."""

        async def gen():
            kurzor = mirror.store.cursor() if after < 0 else int(after)
            verzia = mirror.version
            yield "retry: 3000\n\n"
            # prvý stav hneď (aj keď sa nič nezmenilo) — klient nemusí volať /api/live zvlášť
            for msg in stream_messages(mirror, after=kurzor, deploy=_deploy_state):
                kurzor = max(kurzor, int(msg.get("cursor") or 0), *(r["id"] for r in msg.get("rows") or []))
                yield sse_event(msg)
            ticho = 0.0
            loop = asyncio.get_running_loop()
            while True:
                if await request.is_disconnected():
                    return
                nova = await loop.run_in_executor(None, mirror.wait_for_change, verzia, SSE_WAIT)
                if nova == verzia:
                    ticho += SSE_WAIT
                    if ticho >= SSE_KEEPALIVE:
                        ticho = 0.0
                        yield ": keepalive\n\n"
                    continue
                verzia, ticho = nova, 0.0
                for msg in stream_messages(mirror, after=kurzor, deploy=_deploy_state):
                    kurzor = max(kurzor, int(msg.get("cursor") or 0), *(r["id"] for r in msg.get("rows") or []))
                    yield sse_event(msg)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # -- fáza 2b: účty a nasadenia — len proxy na hub ------------------------- #

    def _deploy_state() -> dict[str, Any]:
        from ...hub import config as hub_config, gitcode

        cfg = hub_config.load()
        return {"configured": cfg is not None, "hub_url": cfg.hub_url if cfg else None,
                "admin": bool(cfg and cfg.admin_token), "version": gitcode.version() or None}

    def _version() -> str | None:
        """Commit tejto webapp — ide k nasadeniu (`version`) a je cieľom „Aktualizovať kód“."""
        from ...hub import gitcode

        return gitcode.version() or None

    def _hub_http(admin: bool = False) -> Any:
        """HTTP na hub: tokenom agenta na čítanie, hlavným tokenom na mutácie (403 bez neho)."""
        from ...hub import config as hub_config
        from ...hub.client import HubHttp

        cfg = hub_config.load()
        if cfg is None:
            raise HTTPException(404, "hub nie je nastavený (karta Hub, alebo python -m tester.hub setup …)")
        if admin and not cfg.admin_token:
            raise HTTPException(403, "účty a nasadenia sa menia len s hlavným tokenom hubu — nastav "
                                     "`admin_token` v tester/agent.json (alebo TRADEBOT_HUB_ADMIN_TOKEN) "
                                     "a reštartuj webapp; bez neho je karta len na čítanie")
        return HubHttp(cfg.hub_url, cfg.admin_token if admin else cfg.token, timeout=15.0)

    def _via_hub(call: Callable[[], Any]) -> Any:
        """Chyba hubu → tá istá HTTP chyba (401/403/404/409/422), hub mimo → 502."""
        from ...hub.client import HubError

        try:
            return call()
        except HubError as exc:
            if exc.status == 404 and str(exc.detail).strip().lower() == "not found":
                raise HTTPException(409, "hub beží na staršom kóde a účty/nasadenia ešte nepozná — "
                                         "aktualizuj a reštartuj hub")
            raise HTTPException(exc.status if exc.status in (401, 403, 404, 409, 422) else 502,
                                exc.detail if isinstance(exc.detail, str) else str(exc))
        except (OSError, ValueError) as exc:
            raise HTTPException(502, f"hub nedostupný: {exc}")

    def _by(user: str | None) -> str:
        from urllib.parse import quote

        return quote(clean_user(user), safe="")

    def _strategy(key: str) -> str:
        k = canonical_key((key or "").strip())
        if k not in STRATEGIES:
            raise HTTPException(422, f"neznáma stratégia {key!r}")
        return k

    def _config_of(strategy: str, profile: str) -> dict[str, Any]:
        """Snímka profilu (repozitár aj vlastné profily testera) — celý config enginu."""
        if not (profile or "").strip():
            raise HTTPException(422, "nasadenie potrebuje profil")
        try:
            return default_params(profile, strategy)[0]
        except (ConfigError, FileNotFoundError, StopIteration) as exc:
            raise HTTPException(422, f"profil {profile!r} stratégie {strategy!r}: {exc}")

    @router.get("/api/live/agents")
    def live_agents():
        """Agenti hubu a čo vedia o live (drivery, počet inštancií) — výber stroja pri účte."""
        http = _hub_http()
        agents = _via_hub(lambda: http.get("/api/agents"))
        return [{"name": a.get("name"), "online": bool(a.get("online")), "last_seen": a.get("last_seen"),
                 "live": a.get("live"), "version": a.get("version"), "needs_restart": bool(a.get("needs_restart")),
                 "updating": bool(a.get("updating")), "code_target": a.get("code_target")} for a in (agents or [])]

    @router.post("/api/live/agents/{name}/update")
    def live_agent_update(name: str, req: LiveCodeUpdateRequest):
        """„Aktualizovať kód na stroji“ (fáza 2c) — na hub s hlavným tokenom; cieľ = commit tejto webapp,
        keď ho požiadavka nenesie."""
        http = _hub_http(admin=True)
        body = {"version": req.version or _version(), "force": bool(req.force)}
        return _via_hub(lambda: http.post(f"/api/live/agents/{name}/update?by={_by(req.user)}", body))

    @router.delete("/api/live/agents/{name}/update")
    def live_agent_update_cancel(name: str, user: str = ""):
        http = _hub_http(admin=True)
        return _via_hub(lambda: http.delete(f"/api/live/agents/{name}/update?by={_by(user)}"))

    @router.get("/api/live/profiles")
    def live_profiles(strategy: str = Query("ibs")):
        """Profily stratégie (repozitár + vlastné) do výberu pri nasadení — ako formulár behu."""
        key = _strategy(strategy)
        return {"strategy": key, "profiles": list_profiles(key), "profile_titles": profile_titles(key)}

    @router.get("/api/live/accounts")
    def live_accounts(agent: str = ""):
        http = _hub_http()
        return _via_hub(lambda: http.get("/api/live/accounts" + (f"?agent={agent}" if agent else "")))

    @router.post("/api/live/accounts")
    def live_account_create(req: LiveAccountRequest):
        """Heslo (ak je) ide na hub raz v tele; tu sa neukladá ani neloguje."""
        http = _hub_http(admin=True)
        body = {k: v for k, v in req.model_dump().items() if k != "user" and v is not None}
        return _via_hub(lambda: http.post(f"/api/live/accounts?by={_by(req.user)}", body))

    @router.patch("/api/live/accounts/{account_id}")
    def live_account_patch(account_id: str, req: LiveAccountRequest):
        http = _hub_http(admin=True)
        body = {k: v for k, v in req.model_dump().items() if k not in ("user", "id") and v is not None}
        return _via_hub(lambda: http.patch(f"/api/live/accounts/{account_id}?by={_by(req.user)}", body))

    @router.delete("/api/live/accounts/{account_id}")
    def live_account_delete(account_id: str, force: bool = False, user: str = ""):
        http = _hub_http(admin=True)
        return _via_hub(lambda: http.delete(
            f"/api/live/accounts/{account_id}?force={'true' if force else 'false'}&by={_by(user)}"))

    @router.get("/api/live/deployments")
    def live_deployments(agent: str = "", account: str = ""):
        http = _hub_http()
        q = "&".join(f"{k}={v}" for k, v in (("agent", agent), ("account", account)) if v)
        return _via_hub(lambda: http.get("/api/live/deployments" + (f"?{q}" if q else "")))

    @router.post("/api/live/deployments")
    def live_deployment_create(req: LiveDeploymentRequest):
        """Config nasadenia sa poskladá tu z profilu (aj vlastného) a na hub ide hotový."""
        http = _hub_http(admin=True)
        strategy = _strategy(req.strategy)
        config = req.config if isinstance(req.config, dict) and req.config else _config_of(strategy, req.profile)
        body = {"account": req.account, "strategy": strategy, "symbol": req.symbol.strip(), "tf": req.tf,
                "profile": req.profile, "config": config, "mode": req.mode, "version": _version()}
        return _via_hub(lambda: http.post(f"/api/live/deployments?by={_by(req.user)}", body))

    @router.patch("/api/live/deployments/{dep_id}")
    def live_deployment_patch(dep_id: str, req: LiveDeploymentPatch):
        """`mode`, `active`, alebo nový `profile` (config sa dopočíta tu) / hotový `config`."""
        http = _hub_http(admin=True)
        body: dict[str, Any] = {}
        if req.mode is not None:
            body["mode"] = req.mode
        if req.active is not None:
            body["active"] = req.active
        if req.profile is not None or isinstance(req.config, dict):
            body["profile"] = req.profile or ""
            if isinstance(req.config, dict) and req.config:
                body["config"] = req.config
            else:
                dep = _via_hub(lambda: http.get(f"/api/live/deployments/{dep_id}"))
                body["config"] = _config_of(dep["strategy"], body["profile"])
            body["version"] = _version()   # nový config = kód, na ktorom vznikol
        return _via_hub(lambda: http.patch(f"/api/live/deployments/{dep_id}?by={_by(req.user)}", body))

    @router.delete("/api/live/deployments/{dep_id}")
    def live_deployment_delete(dep_id: str, force: bool = False, user: str = ""):
        http = _hub_http(admin=True)
        return _via_hub(lambda: http.delete(
            f"/api/live/deployments/{dep_id}?force={'true' if force else 'false'}&by={_by(user)}"))

    @router.get("/api/live/audit")
    def live_audit(limit: int = Query(50, ge=1, le=2000)):
        http = _hub_http()
        return _via_hub(lambda: http.get(f"/api/live/audit?limit={int(limit)}"))

    @router.get("/api/live/{instance}/sessions")
    def live_sessions(instance: str):
        """Behy (sessions) inštancie zo zrkadla, najnovší prvý — výber „Beh“ v detaile."""
        if mirror.store.instance(instance) is None:
            raise HTTPException(404, f"inštancia {instance!r} v zrkadle nie je")
        return mirror.store.sessions(instance)

    @router.get("/api/live/{instance}/snapshot")
    def live_snapshot(instance: str, bars: int | None = Query(None, ge=1, le=5000), session: str = ""):
        """Bez `session` posledných 500 barov naprieč behmi; so `session` celý ten beh (do 5000 barov).
        `cursor` je rowid zrkadla **pred** čítaním — všetko po ňom stránke dopošle stream."""
        kurzor = mirror.store.cursor()
        snap = mirror.store.snapshot(instance, bars=bars, session=session or None)
        if snap["instance"] is None:
            raise HTTPException(404, f"inštancia {instance!r} v zrkadle nie je")
        snap["cursor"] = kurzor
        return snap

    @router.get("/api/live/{instance}/events")
    def live_events(instance: str, after: int = 0, kinds: str = "", limit: int = Query(1000, ge=1, le=10000),
                    session: str = ""):
        druhy = [k.strip() for k in kinds.split(",") if k.strip()] or None
        return mirror.store.events(instance, after=after, kinds=druhy, limit=limit, session=session or None)

    return router
