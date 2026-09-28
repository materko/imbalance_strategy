"""Live telemetria na hube: `/api/live/*` nad `tradebot.live.store.LiveStore` (docs/LIVE.md).

Agent na obchodnom PC posiela dávky zo spoolu (`POST /api/live/events`, idempotentne —
opakovaná dávka nič nezdvojí), webapp si udalosti zrkadlí (`GET /api/live/export?after=`)
a na jednotlivé inštancie sa dá pozrieť aj priamo (`instances`, `events`, `snapshot`).
Hub nepozná stratégiu ani platformu menom — inštancia je len kľúč a `hello` riadok.

Fáza 2b (`add_deploy_routes`): účty a nasadenia ako **požadovaný stav** (`DeployStore`);
mutácie len s hlavným tokenom (`?by=` nesie meno človeka do auditu), čítanie s hocijakým.
Agent si svoj diel berie v heartbeate — sem chodí len webapp.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from tradebot.live.deploy import Conflict, DeployError, DeployStore, NotFound
from tradebot.live.store import LIVE_BARS, LiveStore

__all__ = ["add_live_routes", "add_deploy_routes", "LiveBatch", "LiveEventsRequest"]


class LiveBatch(BaseModel):
    instance: str
    session: str
    events: list[dict[str, Any]] = Field(default_factory=list)


class LiveEventsRequest(BaseModel):
    agent: str
    batches: list[LiveBatch] = Field(default_factory=list)


def add_live_routes(app: FastAPI, state: Any, store: LiveStore, auth: Callable[..., str],
                    own: Callable[[str, str], None]) -> None:
    """Pripojí `/api/live/*`. `auth` a `own` sú tie isté závislosti ako pre ostatné cesty hubu:
    agent s vlastným tokenom posiela len pod svojím menom, správca pod hocijakým."""
    app.state.live = store

    @app.post("/api/live/events")
    def live_events(req: LiveEventsRequest, who: str = Depends(auth)):
        own(who, req.agent)
        if not req.agent.strip():
            raise HTTPException(422, "agent nesmie byť prázdny")
        accepted = 0
        for b in req.batches:
            if not b.instance or not b.session:
                raise HTTPException(422, "dávka potrebuje instance aj session")
            nova = store.instance(b.instance) is None
            n = store.ingest(req.agent, b.instance, b.session, b.events)
            accepted += n
            if nova and n and hasattr(state, "log"):
                # prvýkrát videná inštancia — do logu udalostí hubu, nech je to v `events`
                state.log("live_instance", agent=req.agent, instance=b.instance, session=b.session)
        return {"accepted": accepted}

    @app.get("/api/live/instances")
    def live_instances(who: str = Depends(auth)):
        return store.instances()

    @app.get("/api/live/instances/{instance}")
    def live_instance(instance: str, who: str = Depends(auth)):
        inst = store.instance(instance)
        if inst is None:
            raise HTTPException(404, "inštancia neexistuje")
        return inst

    @app.get("/api/live/instances/{instance}/sessions")
    def live_instance_sessions(instance: str, who: str = Depends(auth)):
        """Behy (sessions) inštancie, najnovší prvý — každý štart stratégie je jeden."""
        if store.instance(instance) is None:
            raise HTTPException(404, "inštancia neexistuje")
        return store.sessions(instance)

    @app.get("/api/live/instances/{instance}/events")
    def live_instance_events(instance: str, after: int = Query(0, ge=0), kinds: str | None = None,
                             limit: int = Query(1000, ge=1, le=20000), session: str | None = None,
                             who: str = Depends(auth)):
        druhy = [k for k in (kinds or "").split(",") if k] or None
        return store.events(instance, after=after, kinds=druhy, limit=limit, session=session or None)

    @app.get("/api/live/instances/{instance}/snapshot")
    def live_instance_snapshot(instance: str, bars: int | None = Query(None, ge=1, le=20000),
                               session: str | None = None, who: str = Depends(auth)):
        return store.snapshot(instance, bars=bars, session=session or None)

    @app.get("/api/live/export")
    def live_export(after: int = Query(0, ge=0), limit: int = Query(5000, ge=1, le=50000),
                    who: str = Depends(auth)):
        return store.export(after=after, limit=limit)


# --------------------------------------------------------------------------- #
# fáza 2b: účty a nasadenia (požadovaný stav) — docs/LIVE.md
# --------------------------------------------------------------------------- #


class AccountRequest(BaseModel):
    """POST/PATCH účtu; `password` sa uloží len ako `secret_pending` a odíde agentovi raz."""
    id: str | None = None
    agent: str | None = None
    platform: str | None = None
    label: str | None = None
    login: str | None = None
    server: str | None = None
    terminal: str | None = None
    portable: bool | None = None
    password: str | None = None

    def fields(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if k != "password" and v is not None}


class DeploymentRequest(BaseModel):
    id: str | None = None
    account: str
    strategy: str
    symbol: str
    tf: int
    profile: str = ""
    config: dict[str, Any] | None = None
    mode: str = "enabled"


class DeploymentPatch(BaseModel):
    mode: str | None = None
    profile: str | None = None
    config: dict[str, Any] | None = None
    active: bool | None = None


def add_deploy_routes(app: FastAPI, state: Any, deploy: DeployStore, store: LiveStore,
                      auth: Callable[..., str], admin: Callable[[str], None]) -> None:
    """`/api/live/accounts*`, `/api/live/deployments*`, `/api/live/audit`: čítanie s hocijakým
    tokenom, mutácie len správca (`admin`). Nasadenie v odpovedi nesie `applied` (čo agent
    naposledy potvrdil) a `live` (či inštancia v spoole žije)."""
    app.state.deploy = deploy

    def _err(exc: Exception) -> HTTPException:
        if isinstance(exc, NotFound):
            return HTTPException(404, str(exc.args[0]) if exc.args else "neexistuje")
        return HTTPException(409 if isinstance(exc, Conflict) else 422, str(exc))

    def _with_live(dep: dict[str, Any]) -> dict[str, Any]:
        """K nasadeniu inštancia zo spoolu: videná? posledná udalosť do `LIVE_BARS` barov TF?"""
        inst = store.instance(dep["instance"]) if dep.get("instance") else None
        if inst is None:
            dep["live"] = {"seen": False, "alive": False, "last_t": None, "last_bar_ms": None,
                           "session": None, "profile": None, "host": None}
            return dep
        now_ms = store.clock() * 1000.0
        okno = LIVE_BARS * max(1, int(dep.get("tf") or 1)) * 60_000
        dep["live"] = {"seen": True, "alive": bool(inst["last_t"]) and (now_ms - inst["last_t"]) <= okno,
                       "last_t": inst["last_t"], "last_bar_ms": inst["last_bar_ms"],
                       "session": inst["last_session"], "profile": inst["profile"], "host": inst["host"]}
        return dep

    # -- účty ------------------------------------------------------------------ #

    @app.get("/api/live/accounts")
    def accounts(agent: str | None = None, who: str = Depends(auth)):
        return deploy.accounts(agent=agent or None)

    @app.post("/api/live/accounts")
    def account_create(req: AccountRequest, by: str = "", who: str = Depends(auth)):
        admin(who)
        try:
            acc = deploy.upsert_account(req.fields(), by=by or who, password=req.password or None)
        except (DeployError, NotFound) as exc:
            raise _err(exc)
        state.log("live_account", account=acc["id"], agent=acc["agent"], action="create")
        return acc

    @app.get("/api/live/accounts/{account_id}")
    def account_get(account_id: str, who: str = Depends(auth)):
        acc = deploy.account(account_id)
        if acc is None:
            raise HTTPException(404, "účet neexistuje")
        return acc

    @app.patch("/api/live/accounts/{account_id}")
    def account_patch(account_id: str, req: AccountRequest, by: str = "", who: str = Depends(auth)):
        admin(who)
        if deploy.account(account_id) is None:
            raise HTTPException(404, "účet neexistuje")
        try:
            acc = deploy.upsert_account({**req.fields(), "id": account_id}, by=by or who,
                                        password=req.password or None)
        except (DeployError, NotFound) as exc:
            raise _err(exc)
        state.log("live_account", account=account_id, agent=acc["agent"], action="update")
        return acc

    @app.delete("/api/live/accounts/{account_id}")
    def account_delete(account_id: str, force: bool = False, by: str = "", who: str = Depends(auth)):
        admin(who)
        try:
            out = deploy.delete_account(account_id, by=by or who, force=force)
        except (DeployError, NotFound) as exc:
            raise _err(exc)
        state.log("live_account", account=account_id, action="delete", deployments=out["deployments"] or None)
        return out

    # -- nasadenia ------------------------------------------------------------- #

    @app.get("/api/live/deployments")
    def deployments(agent: str | None = None, account: str | None = None, who: str = Depends(auth)):
        return [_with_live(d) for d in deploy.deployments(agent=agent or None, account=account or None)]

    @app.post("/api/live/deployments")
    def deployment_create(req: DeploymentRequest, by: str = "", who: str = Depends(auth)):
        admin(who)
        try:
            dep = deploy.create_deployment(req.model_dump(), by=by or who)
        except (DeployError, NotFound) as exc:
            raise _err(exc)
        state.log("live_deployment", deployment=dep["id"], account=dep["account"], agent=dep["agent"],
                  instance=dep["instance"], action="create")
        return _with_live(dep)

    @app.get("/api/live/deployments/{dep_id}")
    def deployment_get(dep_id: str, who: str = Depends(auth)):
        dep = deploy.deployment(dep_id)
        if dep is None:
            raise HTTPException(404, "nasadenie neexistuje")
        return _with_live(dep)

    @app.patch("/api/live/deployments/{dep_id}")
    def deployment_patch(dep_id: str, req: DeploymentPatch, by: str = "", who: str = Depends(auth)):
        admin(who)
        try:
            dep = deploy.update_deployment(dep_id, req.model_dump(), by=by or who)
        except (DeployError, NotFound) as exc:
            raise _err(exc)
        state.log("live_deployment", deployment=dep_id, account=dep["account"], agent=dep["agent"],
                  action="update", mode=dep["mode"], profile=dep["profile"], active=dep["active"])
        return _with_live(dep)

    @app.delete("/api/live/deployments/{dep_id}")
    def deployment_delete(dep_id: str, force: bool = False, by: str = "", who: str = Depends(auth)):
        admin(who)
        try:
            out = deploy.delete_deployment(dep_id, by=by or who, force=force)
        except (DeployError, NotFound) as exc:
            raise _err(exc)
        state.log("live_deployment", deployment=dep_id, action="delete" if out["deleted"] else "deactivate")
        return out

    @app.get("/api/live/audit")
    def audit(limit: int = Query(100, ge=1, le=2000), who: str = Depends(auth)):
        return deploy.audit(limit=limit)
