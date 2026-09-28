"""Live telemetria na hube: `/api/live/*` nad `tradebot.live.store.LiveStore` (docs/LIVE.md).

Agent na obchodnom PC posiela dávky zo spoolu (`POST /api/live/events`, idempotentne —
opakovaná dávka nič nezdvojí), webapp si udalosti zrkadlí (`GET /api/live/export?after=`)
a na jednotlivé inštancie sa dá pozrieť aj priamo (`instances`, `events`, `snapshot`).
Hub nepozná stratégiu ani platformu menom — inštancia je len kľúč a `hello` riadok.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from tradebot.live.store import LiveStore

__all__ = ["add_live_routes", "LiveBatch", "LiveEventsRequest"]


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
