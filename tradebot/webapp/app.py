"""FastAPI aplikácia — REST API nad `store`, `runner` a `gitsync` + statická stránka.

    python -m tradebot.webapp                    # 127.0.0.1:8765
    TRADEBOT_WEB_HOST=0.0.0.0 TRADEBOT_WEB_PORT=8765  # v Dockeri

Žiadne prihlásenie: aplikácia je určená na lokálne spustenie (alebo za reverse
proxy s vlastnou autentifikáciou). Meno testera si tester nastaví v hlavičke
stránky (drží sa v prehliadači) a posiela sa s každým behom aj s Push; predvolené
je `TRADEBOT_USER`, inak `git config user.name`.
"""

from __future__ import annotations

import os

from tradebot.core.env import getenv
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..core.config import ConfigError
from ..strategies import STRATEGIES
from . import chart as chart_data
from . import gitsync
from .pine_meta import param_metadata
from .runner import (
    REPO, BacktestRunner, available_pairs, default_params, list_profiles, profile_instruments, profile_titles, tf_minutes,
)
from .store import RunStore, strategy_of, summarize_for_list

STATIC = Path(__file__).resolve().parent / "static"
_TIMERANGE_RE = re.compile(r"^\d{8}-\d{8}$")


def current_user() -> str:
    return getenv("USER") or gitsync.user_name() or os.environ.get("USERNAME", "") or "tester"


class RunRequest(BaseModel):
    params: dict[str, Any]
    pair: str
    strategy: str = Field("ibs", description="kľúč stratégie z registry (tradebot.strategies.STRATEGIES)")
    timeframe: str = Field("3m", description="TF grafu, na ktorom stratégia počíta (ako v TradingView)")
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
    app = FastAPI(title="TradeBot backtest webapp", version="0.2")
    app.state.store = store
    app.state.runner = runner
    #: Pine defaulty každej stratégie — proti nim sa počítajú odchýlky behu.
    DEFAULTS = {key: spec.config_cls().to_dict() for key, spec in STRATEGIES.items()}
    STRATEGY_META = {
        key: {
            "params": param_metadata(spec),
            "defaults": DEFAULTS[key],
            "profiles": list_profiles(key),
            "profile_titles": profile_titles(key),
            "profile_instruments": profile_instruments(key),
        }
        for key, spec in STRATEGIES.items()
    }

    def defaults_of(rec: dict[str, Any]) -> dict[str, Any]:
        return DEFAULTS.get(strategy_of(rec), DEFAULTS["ibs"])

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/meta")
    def meta():
        pairs = available_pairs()
        return {
            # `params`/`defaults`/`profiles`… na najvyššej úrovni = stratégia "ibs" (spätná
            # kompatibilita pre CLI a testy); stránka pracuje so `strategy_meta[key]`.
            **STRATEGY_META["ibs"],
            "strategies": [spec.public() for spec in STRATEGIES.values()],
            "strategy_meta": STRATEGY_META,
            "pairs": pairs,
            "user": current_user(),
            "branch": gitsync.branch(),
            "queue": runner.snapshot(),
        }

    @app.get("/api/profiles/{name:path}")
    def profile(name: str, strategy: str = Query("ibs")):
        """Názov profilu stratégie (`golden_binance_btcusdt_3m` alebo `ibs/golden_binance_btcusdt_3m`),
        alebo cesta k JSON v repozitári (napr. `docs/profily_archiv/ibs/x.json`)."""
        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        target: str | Path = name
        if name.endswith(".json"):
            path = (REPO / name).resolve()
            if not path.is_relative_to(REPO) or path.suffix != ".json" or not path.exists():
                raise HTTPException(404, f"profil {name!r} nie je JSON v repozitári")
            target = path
        elif "/" in name:
            strategy = name.split("/", 1)[0]  # "ibs/golden_..." nesie stratégiu v názve
            if strategy not in STRATEGIES:
                raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        try:
            params, instrument = default_params(target, strategy)
        except (ConfigError, FileNotFoundError) as exc:
            raise HTTPException(404, str(exc))
        return {"name": name, "strategy": strategy, "params": params, "instrument": instrument}

    @app.get("/api/runs")
    def runs(q: str = "", limit: int = 500):
        recs = store.search(q) if q.strip() else store.all()
        return {"total": len(recs), "runs": [summarize_for_list(r, defaults_of(r)) for r in recs[:limit]]}

    @app.post("/api/runs")
    def submit(req: RunRequest):
        if not _TIMERANGE_RE.match(req.timerange):
            raise HTTPException(422, "timerange musí byť YYYYMMDD-YYYYMMDD")
        a, b = req.timerange.split("-")
        if a >= b:
            raise HTTPException(422, "začiatok obdobia musí byť pred koncom")
        if req.strategy not in STRATEGIES:
            raise HTTPException(422, f"neznáma stratégia {req.strategy!r}; známe: {sorted(STRATEGIES)}")
        if req.timeframe not in chart_data.TIMEFRAMES:
            raise HTTPException(422, f"timeframe {req.timeframe!r} nie je podporovaný ({', '.join(chart_data.TIMEFRAMES)})")
        if req.timeframe not in chart_data.available_timeframes(req.pair):
            raise HTTPException(422, f"pre {req.pair} nie sú stiahnuté {req.timeframe} dáta")
        detail = req.timeframe_detail or None
        if detail and tf_minutes(detail) >= tf_minutes(req.timeframe):
            detail = None  # detail fillov musí byť jemnejší než TF grafu, inak ho Freqtrade odmietne
        settings = {
            "strategy": req.strategy,
            "pair": req.pair,
            "timeframe": req.timeframe,
            "timerange": req.timerange,
            "fee": req.fee,
            "wallet": req.wallet,
            "timeframe_detail": detail,
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
        defaults = defaults_of(rec)
        rec["overrides"] = {k: v for k, v in rec.get("params", {}).items()
                            if not k.startswith("_") and defaults.get(k) != v}
        rec["has_chart"] = store.has_chart(run_id)
        return {"record": rec, "trades": store.trades(run_id), "live": False}

    @app.get("/api/runs/{run_id}/chart")
    def run_chart(run_id: str, start: int | None = Query(None, alias="from"),
                  end: int | None = Query(None, alias="to")):
        """Kresby enginu z behu, orezané na okno `from`–`to` (ms epoch)."""
        data = store.chart(run_id)
        if data is None:
            if store.get(run_id) is None:
                raise HTTPException(404, "beh neexistuje")
            raise HTTPException(404, "beh nemá uložené kresby (spustený staršou verziou)")
        objects = data["objects"] if start is None or end is None else chart_data.window(data, start, end)
        return {"meta": chart_data.summary(data), "objects": objects}

    @app.get("/api/candles")
    def candles(pair: str, tf: str = "3m", start: int = Query(..., alias="from"),
                end: int = Query(..., alias="to")):
        """Sviečky páru v okne `from`–`to` (ms epoch), najviac `MAX_CANDLES`."""
        if end <= start:
            raise HTTPException(422, "to musí byť väčšie než from")
        try:
            return chart_data.candles(pair, tf, start, end)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc))

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
        params["_strategy"] = strategy_of(rec)
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
