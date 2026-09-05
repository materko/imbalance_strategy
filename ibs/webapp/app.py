"""FastAPI aplikácia — REST API nad `store`, `runner` a `gitsync` + statická stránka.

    python -m ibs.webapp                    # 127.0.0.1:8765
    IBS_WEB_HOST=0.0.0.0 IBS_WEB_PORT=8765  # v Dockeri

Žiadne prihlásenie: aplikácia je určená na lokálne spustenie (alebo za reverse
proxy s vlastnou autentifikáciou). Meno testera si tester nastaví v hlavičke
stránky (drží sa v prehliadači) a posiela sa s každým behom aj s Push; predvolené
je `IBS_USER`, inak `git config user.name`.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..core import IBSConfig
from ..core.config import ConfigError
from . import gitsync
from .pine_meta import param_metadata
from .runner import BacktestRunner, available_pairs, default_params, list_profiles
from .store import RunStore, summarize_for_list

STATIC = Path(__file__).resolve().parent / "static"
_TIMERANGE_RE = re.compile(r"^\d{8}-\d{8}$")


def current_user() -> str:
    return os.environ.get("IBS_USER") or gitsync.user_name() or os.environ.get("USERNAME", "") or "tester"


class RunRequest(BaseModel):
    params: dict[str, Any]
    pair: str
    timerange: str = Field(..., description="YYYYMMDD-YYYYMMDD")
    fee: float | None = Field(0.0005, description="poplatok na stranu ako podiel (0.0005 = 0,05 %)")
    wallet: float = 10000
    timeframe_detail: str | None = "1m"
    profile: str | None = None
    note: str = ""
    user: str | None = Field(None, max_length=80, description="meno testera z hlavičky stránky")


class GitPushRequest(BaseModel):
    author: str | None = Field(None, max_length=80)
    message: str | None = Field(None, max_length=200)


def _clean_user(name: str | None) -> str:
    name = (name or "").strip()
    return name[:80] if name else current_user()


def create_app(store: RunStore | None = None, runner: BacktestRunner | None = None) -> FastAPI:
    store = store or RunStore()
    runner = runner or BacktestRunner(store)
    app = FastAPI(title="IBS backtest webapp", version="0.1")
    app.state.store = store
    app.state.runner = runner
    defaults = IBSConfig().to_dict()

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/meta")
    def meta():
        pairs = available_pairs()
        return {
            "params": param_metadata(),
            "defaults": defaults,
            "profiles": list_profiles(),
            "pairs": pairs,
            "user": current_user(),
            "branch": gitsync.branch(),
            "queue": runner.snapshot(),
        }

    @app.get("/api/profiles/{name}")
    def profile(name: str):
        try:
            params, instrument = default_params(name)
        except (ConfigError, FileNotFoundError) as exc:
            raise HTTPException(404, str(exc))
        return {"name": name, "params": params, "instrument": instrument}

    @app.get("/api/runs")
    def runs(q: str = "", limit: int = 500):
        recs = store.search(q) if q.strip() else store.all()
        return {"total": len(recs), "runs": [summarize_for_list(r, defaults) for r in recs[:limit]]}

    @app.post("/api/runs")
    def submit(req: RunRequest):
        if not _TIMERANGE_RE.match(req.timerange):
            raise HTTPException(422, "timerange musí byť YYYYMMDD-YYYYMMDD")
        a, b = req.timerange.split("-")
        if a >= b:
            raise HTTPException(422, "začiatok obdobia musí byť pred koncom")
        settings = {
            "pair": req.pair,
            "timerange": req.timerange,
            "fee": req.fee,
            "wallet": req.wallet,
            "timeframe_detail": req.timeframe_detail or None,
            "profile": req.profile,
        }
        try:
            job = runner.submit(req.params, settings, note=req.note, user=_clean_user(req.user))
        except (ConfigError, ValueError) as exc:
            raise HTTPException(422, str(exc))
        return job.public()

    @app.get("/api/queue")
    def queue():
        return runner.snapshot()

    @app.post("/api/queue/{job_id}/cancel")
    def cancel(job_id: str):
        if not runner.cancel(job_id):
            raise HTTPException(404, "beh nie je vo fronte ani nebeží")
        return {"ok": True}

    @app.get("/api/runs/{run_id}")
    def run(run_id: str):
        rec = store.get(run_id)
        if rec is None:
            job = runner.job(run_id)
            if job is None:
                raise HTTPException(404, "beh neexistuje")
            return {"record": job.public(), "trades": [], "live": True}
        rec["overrides"] = {k: v for k, v in rec.get("params", {}).items()
                            if not k.startswith("_") and defaults.get(k) != v}
        return {"record": rec, "trades": store.trades(run_id), "live": False}

    @app.get("/api/runs/{run_id}/log", response_class=PlainTextResponse)
    def run_log(run_id: str):
        job = runner.job(run_id)
        if job is not None and job.status in ("queued", "running"):
            return "\n".join(job.log_lines[-400:])
        return store.log(run_id)

    @app.get("/api/runs/{run_id}/profile.json")
    def run_profile(run_id: str):
        rec = store.get(run_id)
        if rec is None:
            raise HTTPException(404, "beh neexistuje")
        params = dict(rec["params"])
        params["_comment"] = [f"profil z behu {run_id} ({rec.get('settings', {}).get('pair')}, "
                              f"{rec.get('settings', {}).get('timerange')}) - export z webapp"]
        from .runner import instrument_for_pair
        params["_instrument"] = instrument_for_pair(rec["settings"]["pair"])
        return JSONResponse(params, headers={"Content-Disposition": f'attachment; filename="{run_id}.json"'})

    @app.delete("/api/runs/{run_id}")
    def delete(run_id: str):
        if not store.delete(run_id):
            raise HTTPException(404, "beh neexistuje")
        return {"ok": True}

    @app.get("/api/git/status")
    def git_status():
        return gitsync.status()

    @app.post("/api/git/pull")
    def git_pull():
        return gitsync.pull()

    @app.post("/api/git/push")
    def git_push(req: GitPushRequest | None = None):
        req = req or GitPushRequest()
        return gitsync.push(message=req.message, author=_clean_user(req.author))

    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
    return app


def default_timerange(pairs: list[dict[str, Any]]) -> str:
    """Posledných 365 dní dostupných dát — rozumný štart pre tabuľku."""
    to = max((p["to"] for p in pairs), default=str(date.today()))
    end = datetime.strptime(to, "%Y-%m-%d")
    start = end - timedelta(days=365)
    return f"{start:%Y%m%d}-{end:%Y%m%d}"


app = create_app()
