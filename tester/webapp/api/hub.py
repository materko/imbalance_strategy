"""Distribuované počítanie cez tester.hub (`/api/hub*`)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException

from tradebot.core.config import ConfigError
from tradebot.strategies import get_spec

from .common import clean_user
from .context import AppContext
from .models import (
    HubJobRequest, HubOptions, HubRunRequest, HubHyperoptRequest, HubAcceptRequest,
    HubConfigRequest,
)
from .settings import run_settings


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    runner = ctx.runner
    app = ctx.app
    DEFAULTS = ctx.defaults

    # -- distribuované počítanie (tester.hub) --------------------------------- #
    # Webapp je agent hubu, keď má klon tester/agent.json (agenta štartuje __main__).
    # Zadanie ide cez webapp preto, aby si jej agent zapísal, čo poslal, a výsledok
    # po dobehnutí vyzdvihol sám — aj keď CLI, ktoré ho zadalo, už nebeží.

    def _hub_client():
        from ...hub import config as hub_config
        from ...hub.client import HubClient

        cfg = hub_config.load()
        if cfg is None:
            raise HTTPException(404, "hub nie je nastavený (python -m tester.hub setup …)")
        try:
            return cfg, HubClient.from_config(cfg)
        except PermissionError as exc:
            raise HTTPException(403, str(exc))

    def start_hub_agent(cfg) -> Any:
        """(Re)štart agenta hubu v tomto procese — pri štarte webapp aj po uložení nastavení."""
        from ...hub.agent import HubAgent

        stary = getattr(app.state, "hub_agent", None)
        if stary is not None:
            stary.stop()
            try:
                stary.bye()
            except Exception:  # noqa: BLE001 - starý hub nemusí byť dostupný
                pass
        agent = HubAgent(cfg, runner, store)
        if cfg.accept:
            runner.workers = agent.slots
        agent.start()
        app.state.hub_agent = agent
        return agent

    app.state.start_hub_agent = start_hub_agent

    @router.post("/api/hub/config")
    def hub_config_save(req: HubConfigRequest):
        """Uloží `tester/agent.json` a agenta hneď (re)štartuje — bez reštartu webapp."""
        from ...hub import config as hub_config

        url = req.hub_url.strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            raise HTTPException(422, "adresa hubu musí začínať http:// alebo https://")
        stary = hub_config.load()
        token = req.token.strip() or (stary.token if stary else "")
        cfg = hub_config.AgentConfig(name=req.name.strip(), hub_url=url, token=token,
                                     accept=req.accept, send=req.send, max_parallel=req.max_parallel)
        hub_config.save(cfg)
        start_hub_agent(hub_config.load() or cfg)
        return hub_status()

    @router.delete("/api/hub/config")
    def hub_config_delete():
        """Odpojiť: agent sa odhlási a config sa zmaže."""
        from ...hub import config as hub_config

        agent = getattr(app.state, "hub_agent", None)
        if agent is not None:
            agent.stop()
            try:
                agent.bye()
            except Exception:  # noqa: BLE001
                pass
            app.state.hub_agent = None
        hub_config.AGENT_CONFIG.unlink(missing_ok=True)
        return hub_status()

    @router.get("/api/hub")
    def hub_status():
        """Konfigurácia agenta, jeho stav a (keď smie posielať) prehľad hubu."""
        from ...hub import config as hub_config
        from ...hub.client import HubClient

        cfg = hub_config.load()
        agent = getattr(app.state, "hub_agent", None)
        out: dict[str, Any] = {"configured": cfg is not None, "config": cfg.public() if cfg else None,
                               "agent": agent.public() if agent else None, "hub": None, "error": None}
        if cfg and cfg.send:
            try:
                out["hub"] = HubClient.from_config(cfg).status()
            except Exception as exc:  # noqa: BLE001 - hub mimo nesmie zhodiť stav webapp
                out["error"] = f"{type(exc).__name__}: {exc}"
        return out

    def _hub_send(kind: str, payload: dict[str, Any], *, cores, queue, max_wait_seconds,
                  estimate_seconds, note, version, max_seconds) -> dict[str, Any]:
        from ...hub import gitcode
        from ...hub.client import HubError, NoCapacityError

        cfg, client = _hub_client()
        try:
            job = client.submit(kind, payload, cores=cores, queue=queue,
                                max_wait_seconds=max_wait_seconds, estimate_seconds=estimate_seconds,
                                note=note, version=version or gitcode.version() or None,
                                max_seconds=max_seconds)
        except NoCapacityError as exc:
            raise HTTPException(409, exc.detail)
        except HubError as exc:
            raise HTTPException(502, str(exc))
        except (ValueError, OSError) as exc:
            raise HTTPException(502, f"hub nedostupný: {exc}")
        agent = getattr(app.state, "hub_agent", None)
        if agent is not None:
            agent.note_sent(job, note)
        return job

    @router.post("/api/hub/jobs")
    def hub_submit(req: HubJobRequest):
        """Hotový payload (CLI): pošle sa tak, ako prišiel."""
        return _hub_send(req.kind, req.payload, cores=req.cores, queue=req.queue,
                         max_wait_seconds=req.max_wait_seconds, estimate_seconds=req.estimate_seconds,
                         note=req.note, version=req.version, max_seconds=req.max_seconds)

    def _hub_form(req: HubOptions, kind: str, params: dict[str, Any], settings: dict[str, Any],
                  note: str, user: str) -> dict[str, Any]:
        """Zadanie z formulára: settings overené ako pri lokálnom behu, odhad z tejto histórie."""
        from ...hub import protocol as P

        payload = {"params": params, "settings": settings, "note": note, "user": user or None}
        odhad = P.estimate_seconds(settings, store.all(), cores=os.cpu_count() or 1)
        return _hub_send(kind, payload, cores=req.cores, queue=req.queue,
                         max_wait_seconds=req.max_wait_minutes * 60 if req.max_wait_minutes else None,
                         estimate_seconds=odhad, note=note, version=None,
                         max_seconds=req.max_runtime_minutes * 60 if req.max_runtime_minutes else None)

    @router.post("/api/hub/runs")
    def hub_run(req: HubRunRequest):
        """Beh z formulára na hub — rovnaká validácia ako `/api/runs`, len ho spočíta agent."""
        settings = run_settings(req)
        try:
            get_spec(req.strategy).config_cls.from_dict(
                {k: v for k, v in req.params.items() if not k.startswith("_")})
        except ConfigError as exc:
            raise HTTPException(422, str(exc))
        return _hub_form(req, "backtest", req.params, settings, req.note, clean_user(req.user))

    @router.post("/api/hub/hyperopts")
    def hub_hyperopt(req: HubHyperoptRequest):
        """Hyperopt z formulára na hub — rovnaké zadanie ako `/api/hyperopts`."""
        from ... import hyperopt as ho

        if not req.space:
            raise HTTPException(422, "hyperopt potrebuje aspoň jeden parameter")
        defaults = DEFAULTS.get(req.strategy) or DEFAULTS["ibs"]
        for name in req.space:
            if name not in defaults:
                raise HTTPException(422, f"neznámy parameter {name!r}")
        try:
            ho.build_plan(req.space, strategy=req.strategy, goal=req.goal,
                          max_dd=req.max_dd, min_trades=req.min_trades, note=req.note)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        settings = {**run_settings(req), "hyperopt": {
            "knobs": dict(req.space), "goal": req.goal, "max_dd": req.max_dd,
            "min_trades": req.min_trades, "epochs": req.epochs, "seed": req.seed,
            "verify": req.verify,
        }}
        popis = ", ".join(f"{k}={v}" for k, v in req.space.items())
        note = f"hyperopt {popis}" + (f" — {req.note}" if req.note else "")
        return _hub_form(req, "hyperopt", req.params, settings, note, clean_user(req.user))

    @router.post("/api/hub/accept")
    def hub_accept(req: HubAcceptRequest):
        """Prepnúť prijímanie výpočtov na tejto webapp — bez reštartu, zapíše sa do configu."""
        agent = getattr(app.state, "hub_agent", None)
        if agent is None:
            raise HTTPException(404, "táto webapp nebeží ako agent hubu (tester/agent.json + reštart)")
        agent.set_accept(req.accept)
        return agent.public()

    @router.delete("/api/hub/agents/{name}")
    def hub_forget_agent(name: str, force: bool = False, token: bool = False):
        """Vyhodiť agenta z hubu — premenovaný stroj, ktorý tam visí ako offline.
        Hub to dovolí len správcovskému tokenu."""
        from ...hub.client import HubError

        _, client = _hub_client()
        try:
            return client.forget_agent(name, force=force, with_token=token)
        except HubError as exc:
            if exc.status == 404 and str(exc.detail).strip().lower() == "not found":
                # Nie „agenta nepoznám", ale „takú cestu nepoznám": hub stojí na starom kóde.
                raise HTTPException(409, "hub beží na staršom kóde a vyhadzovanie agentov ešte "
                                         "nepozná — aktualizuj a reštartuj hub (git pull + reštart "
                                         "služby/kontajnera), alebo to sprav na jeho stroji: "
                                         f"python -m tester.hub forget \"{name}\" --local")
            raise HTTPException(exc.status if exc.status in (401, 403, 404, 409) else 502, str(exc))

    @router.get("/api/hub/jobs")
    def hub_jobs(live: bool = True):
        from ...hub.client import HubError

        _, client = _hub_client()
        try:
            return client.jobs(live=live)
        except HubError as exc:
            raise HTTPException(exc.status if exc.status in (404, 401) else 502, str(exc))

    @router.get("/api/hub/jobs/{job_id}")
    def hub_job(job_id: str):
        from ...hub.client import HubError

        _, client = _hub_client()
        try:
            return client.job(job_id)
        except HubError as exc:
            raise HTTPException(exc.status if exc.status in (404, 401) else 502, str(exc))

    @router.post("/api/hub/jobs/{job_id}/cancel")
    def hub_cancel(job_id: str):
        from ...hub.client import HubError

        _, client = _hub_client()
        try:
            return client.cancel(job_id)
        except HubError as exc:
            raise HTTPException(exc.status if exc.status in (404, 401) else 502, str(exc))

    return router
