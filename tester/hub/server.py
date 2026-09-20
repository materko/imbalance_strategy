"""Hub: zoznam agentov, fronta výpočtov, odovzdané výsledky — a REST API nad tým.

    python -m tester.hub serve --host 0.0.0.0 --port 8790      # TRADEBOT_HUB_TOKEN=…

Stav (`HubState`) je jeden slovník agentov a jeden slovník výpočtov, po každej zmene
zapísaný do `tester/hub_data/state.json` — keď hub spadne s piatimi výpočtami vo fronte,
po štarte tam stále sú. Zipy výsledkov ležia vedľa (`results/<id>.zip`), kým si ich
zadávateľ nevyzdvihne a nepotvrdí (`ack`).

Životný cyklus výpočtu:

```
queued ──► assigned ──► running ──► done / failed
   │            │           │
   └────────────┴───────────┴──► cancelling ──► cancelled
```

- `queued`     čaká na voľného agenta (len keď zadávateľ súhlasil s frontou)
- `assigned`   hub ho pridelil agentovi, agent si ho vezme pri najbližšom heartbeate
- `running`    agent hlási postup a odhad zvyšku
- `cancelling` niekto (zadávateľ, alebo správca hubu) výpočet zrušil; hub to povie
               počítajúcemu agentovi v heartbeate a čaká, kým beh zabije
- hotový výpočet dostane zadávateľ v **svojom** heartbeate (`finished`) — hub vie, komu
  patrí, lebo výpočet nesie meno zadávateľa; po `ack` sa zip zmaže

Agent, ktorý sa prestane hlásiť (`agent_timeout`), je offline: čo mu bolo pridelené a
ešte nebežalo, ide späť do fronty; čo bežalo, sa raz skúsi znova (ak výpočet frontu
dovolil), inak zlyhá s chybou „agent sa odmlčal".

**Agent medzitým počíta ďalej** — hub potrebuje len na odovzdanie. Keď sa vráti, hub mu
výpočet vráti (`_readopt`, ak naň ešte nikto iný nesadol) a **neskorý výsledok prijme aj
vtedy, keď ho už odpísal**: hotový beh prepíše „agent sa odmlčal" a zadávateľ ho dostane
v svojom heartbeate. Keď to medzitým dopočítal niekto iný, platí prvý hotový a druhý sa
zahodí; agentovi, ktorý hlási už zbytočný výpočet, hub pošle `cancel`. To isté platí, keď
spadne hub: agenti dopočítajú, čo majú, a odovzdajú to po jeho návrate (stav je na disku).

Tokeny: hlavný token (`TRADEBOT_HUB_TOKEN`) je správcovský — smie všetko. Každý agent má
vlastný token (`tokens.json`, `python -m tester.hub token add <meno>`), ktorý ho zároveň
**identifikuje**: s ním sa hlási len pod svojím menom, zadáva výpočty len ako on a
výsledky číta len k svojim. Hub bez jediného tokenu (vývoj na localhoste) je otvorený.

Log udalostí (`events.jsonl`, riadok na udalosť): kto sa prihlásil a odhlásil, kto čo
zadal, komu to hub pridelil, kedy beh začal a ako skončil, kto čo zrušil. Číta sa cez
`GET /api/events` a `python -m tester.hub events`.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import protocol as P
from .events import EVENTS_KEEP
from .state import (  # noqa: F401 — verejné mená z čias pred rozdelením
    DEFAULT_AGENT_TIMEOUT, KEEP_FINISHED, MAX_ATTEMPTS, HubState, NameTaken, NoCapacity,
)
from .tokens import ADMIN  # noqa: F401


__all__ = ["HubState", "NoCapacity", "NameTaken", "create_hub_app", "DEFAULT_PORT"]

DEFAULT_PORT = 8790


# --------------------------------------------------------------------------- #
# FastAPI
# --------------------------------------------------------------------------- #


class RegisterRequest(BaseModel):
    name: str
    instance: str
    cores: int = 1
    slots: int = 1
    accept: bool = True
    send: bool = True
    version: str = ""


class HeartbeatRequest(BaseModel):
    instance: str | None = None
    accept: bool | None = None
    send: bool | None = None
    cores: int | None = None
    slots: int | None = None
    version: str | None = None
    needs_restart: bool | None = None
    load: dict[str, Any] = Field(default_factory=dict)
    jobs: list[dict[str, Any]] = Field(default_factory=list)


class SubmitRequest(BaseModel):
    kind: str
    payload: dict[str, Any]
    submitter: str
    cores: int | str | None = None
    queue: bool = False
    max_wait_seconds: float | None = None
    estimate_seconds: float | None = None
    note: str = ""
    version: str | None = None
    max_seconds: float | None = None


def create_hub_app(state: HubState | None = None) -> FastAPI:
    state = state or HubState()
    app = FastAPI(title="TradeBot hub", version="0.2")
    app.state.hub = state

    def auth(request: Request) -> str:
        """Identita volajúceho podľa tokenu: `ADMIN`, alebo meno agenta."""
        hlavicka = request.headers.get("authorization") or ""
        token = hlavicka[7:] if hlavicka.lower().startswith("bearer ") else request.headers.get("x-hub-token", "")
        who = state.identity(token or None)
        if who is None:
            raise HTTPException(401, "neplatný token hubu (TRADEBOT_HUB_TOKEN, alebo token agenta)")
        return who

    def own(who: str, name: str) -> None:
        """Agent s vlastným tokenom koná len pod svojím menom; správca pod hocijakým."""
        if who != ADMIN and who != name:
            raise HTTPException(403, f"token patrí agentovi {who!r}, nie {name!r}")

    def admin(who: str) -> None:
        if who != ADMIN:
            raise HTTPException(403, "len správca hubu (hlavný token)")

    def _job_or_404(job_id: str, with_payload: bool = False) -> dict[str, Any]:
        j = state.job(job_id, with_payload=with_payload)
        if j is None:
            raise HTTPException(404, "výpočet neexistuje")
        return j

    def party(who: str, j: dict[str, Any]) -> None:
        """Zadávateľ alebo počítajúci agent (alebo správca)."""
        if who != ADMIN and who not in (j.get("submitter"), j.get("agent")):
            raise HTTPException(403, f"výpočet {j['id']} nepatrí agentovi {who!r}")

    @app.get("/api/health")
    def health():
        return {"ok": True, "hub": True, "online": state.overview()["online"]}

    @app.get("/api/status")
    def status(who: str = Depends(auth)):
        return state.overview()

    @app.post("/api/agents/register")
    def register(req: RegisterRequest, who: str = Depends(auth)):
        own(who, req.name)
        try:
            return state.register(req.name, instance=req.instance, cores=req.cores, slots=req.slots,
                                  accept=req.accept, send=req.send, version=req.version)
        except NameTaken as exc:
            raise HTTPException(409, str(exc))
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/api/agents")
    def agents(who: str = Depends(auth)):
        return state.overview()["agents"]

    @app.post("/api/agents/{name}/accept")
    def accept(name: str, value: bool = True, who: str = Depends(auth)):
        admin(who)
        try:
            return state.request_accept(name, value)
        except KeyError:
            raise HTTPException(404, f"agent {name!r} nie je zaregistrovaný")

    @app.delete("/api/agents/{name}")
    def forget_agent(name: str, force: bool = False, token: bool = False, who: str = Depends(auth)):
        """Vyhodiť agenta zo zoznamu (premenovaný stroj, zrušený agent) — správca hubu."""
        admin(who)
        try:
            return state.forget(name, force=force, with_token=token, by="hub")
        except KeyError:
            raise HTTPException(404, f"agent {name!r} nie je zaregistrovaný")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.post("/api/agents/{name}/bye")
    def bye(name: str, who: str = Depends(auth)):
        own(who, name)
        try:
            return state.bye(name)
        except KeyError:
            raise HTTPException(404, f"agent {name!r} nie je zaregistrovaný")

    @app.post("/api/agents/{name}/heartbeat")
    def heartbeat(name: str, req: HeartbeatRequest, who: str = Depends(auth)):
        own(who, name)
        try:
            return state.heartbeat(name, req.model_dump())
        except KeyError:
            raise HTTPException(404, f"agent {name!r} nie je zaregistrovaný — najprv /api/agents/register")

    @app.get("/api/capacity")
    def capacity(cores: str = Query("1"), who: str = Depends(auth)):
        demand: int | str = P.ALL if cores == P.ALL else max(1, int(cores))
        return state.capacity(demand)

    @app.post("/api/jobs")
    def submit(req: SubmitRequest, who: str = Depends(auth)):
        own(who, req.submitter)
        try:
            return state.submit(kind=req.kind, payload=req.payload, submitter=req.submitter,
                                cores=req.cores, queue=req.queue, max_wait_seconds=req.max_wait_seconds,
                                estimate_seconds=req.estimate_seconds, note=req.note,
                                version=req.version, max_seconds=req.max_seconds)
        except NoCapacity as exc:
            raise HTTPException(409, exc.detail())
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/api/jobs")
    def jobs(live: bool = False, submitter: str | None = None, who: str = Depends(auth)):
        return state.list_jobs(live_only=live, submitter=submitter)

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str, payload: bool = False, who: str = Depends(auth)):
        j = _job_or_404(job_id, with_payload=payload)
        if payload:
            party(who, j)  # parametre behu vidí len ten, koho sa týkajú
        return j

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel(job_id: str, by: str = "", who: str = Depends(auth)):
        j = _job_or_404(job_id)
        party(who, j)
        return state.cancel(job_id, by=(by or who) if who != ADMIN else (by or "hub"))

    @app.post("/api/jobs/{job_id}/result")
    async def result(job_id: str, request: Request, status: str = "done", error: str | None = None,
                     run_ids: str = "", agent: str | None = None, version: str | None = None,
                     who: str = Depends(auth)):
        if who != ADMIN:
            if agent and agent != who:
                raise HTTPException(403, f"token patrí agentovi {who!r}, nie {agent!r}")
            agent = who
        data = await request.body()
        try:
            return state.result(job_id, data, status=status, error=error,
                                run_ids=[r for r in run_ids.split(",") if r], agent=agent,
                                version=version or None)
        except KeyError:
            raise HTTPException(404, "výpočet neexistuje")
        except PermissionError as exc:
            raise HTTPException(403, str(exc))
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/api/jobs/{job_id}/result")
    def result_download(job_id: str, who: str = Depends(auth)):
        j = _job_or_404(job_id)
        if who != ADMIN and who != j.get("submitter"):
            raise HTTPException(403, f"výsledok patrí zadávateľovi {j.get('submitter')!r}")
        p = state.result_path(job_id)
        if not p.exists():
            raise HTTPException(410, "výsledok už nie je na hube (vyzdvihnutý, alebo beh nemal výsledok)")
        return FileResponse(p, media_type="application/zip", filename=p.name)

    @app.post("/api/jobs/{job_id}/ack")
    def ack(job_id: str, who: str = Depends(auth)):
        j = _job_or_404(job_id)
        if who != ADMIN and who != j.get("submitter"):
            raise HTTPException(403, f"výsledok patrí zadávateľovi {j.get('submitter')!r}")
        return state.ack(job_id)

    @app.delete("/api/jobs/{job_id}")
    def delete(job_id: str, who: str = Depends(auth)):
        j = _job_or_404(job_id)
        if who != ADMIN and who != j.get("submitter"):
            raise HTTPException(403, f"výpočet patrí zadávateľovi {j.get('submitter')!r}")
        if not state.delete(job_id):
            raise HTTPException(409, "výpočet ešte žije")
        return {"ok": True}

    # -- tokeny a log udalostí ------------------------------------------------ #

    @app.get("/api/tokens")
    def tokens(who: str = Depends(auth)):
        admin(who)
        return state.token_names()

    @app.post("/api/tokens/{name}")
    def token_add(name: str, who: str = Depends(auth)):
        admin(who)
        try:
            return {"name": name, "token": state.add_token(name)}
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.delete("/api/tokens/{name}")
    def token_remove(name: str, who: str = Depends(auth)):
        admin(who)
        if not state.remove_token(name):
            raise HTTPException(404, f"agent {name!r} token nemá")
        return {"ok": True}

    @app.get("/api/events")
    def events(limit: int = Query(100, ge=1, le=EVENTS_KEEP), job: str | None = None,
               agent: str | None = None, event: str | None = None, who: str = Depends(auth)):
        return state.events(limit=limit, job=job, agent=agent, event=event)

    return app
