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
from . import profiles as user_profiles
from .pine_meta import param_metadata
from .runner import (
    REPO, BacktestRunner, available_pairs, default_params, instrument_for_pair, list_profiles,
    profile_instruments, profile_titles, tf_minutes,
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


class ProfileSaveRequest(BaseModel):
    """Nový vlastný profil — buď z behu (`from_run`), alebo priamo z parametrov."""

    name: str = Field(..., max_length=48)
    strategy: str = Field("ibs", description="stratégia profilu; pri `from_run` sa berie z behu")
    from_run: str | None = None
    params: dict[str, Any] | None = None
    instrument: str | None = None
    timeframe: str | None = Field(None, description="TF grafu, na ktorom je profil ladený")
    timerange: str | None = None
    fee: float | None = None
    wallet: float | None = None
    timeframe_detail: str | None = None
    base: str | None = Field(None, max_length=200, description="profil, z ktorého sa vychádzalo")
    note: str = Field("", max_length=200)
    overwrite: bool = False


class ProfileRenameRequest(BaseModel):
    name: str = Field(..., max_length=48)


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
    #: Metadáta formulára stratégie. Parametre a defaulty sú kód (nemenia sa za behu),
    #: zoznam profilov sa číta vždy nanovo — tester si ich cez API ukladá, premenúva a maže.
    PARAM_META = {key: param_metadata(spec) for key, spec in STRATEGIES.items()}

    def strategy_meta(key: str) -> dict[str, Any]:
        return {
            "params": PARAM_META[key],
            "defaults": DEFAULTS[key],
            "profiles": list_profiles(key),
            "profile_titles": profile_titles(key),
            "profile_instruments": profile_instruments(key),
            "user_profiles": user_profiles.user_names(key),
        }

    def defaults_of(rec: dict[str, Any]) -> dict[str, Any]:
        return DEFAULTS.get(strategy_of(rec), DEFAULTS["ibs"])

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/meta")
    def meta():
        pairs = available_pairs()
        by_key = {key: strategy_meta(key) for key in STRATEGIES}
        return {
            # `params`/`defaults`/`profiles`… na najvyššej úrovni = stratégia "ibs" (spätná
            # kompatibilita pre CLI a testy); stránka pracuje so `strategy_meta[key]`.
            **by_key["ibs"],
            "strategies": [spec.public() for spec in STRATEGIES.values()],
            "strategy_meta": by_key,
            "pairs": pairs,
            "user": current_user(),
            "branch": gitsync.branch(),
            "queue": runner.snapshot(),
        }

    @app.get("/api/profiles")
    def profiles_list(strategy: str = Query("ibs")):
        """Profily stratégie do formulára: z repozitára (nemenné) a vlastné (menné aj mazateľné)."""
        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        return {"strategy": strategy, "profiles": list_profiles(strategy), "user_profiles": user_profiles.user_names(strategy),
                "profile_titles": profile_titles(strategy), "profile_instruments": profile_instruments(strategy)}

    @app.post("/api/profiles")
    def profile_save(req: ProfileSaveRequest):
        params, instrument, comment = req.params, req.instrument, req.note or None
        strategy = req.strategy
        setup = {"timeframe": req.timeframe, "timerange": req.timerange, "fee": req.fee,
                 "wallet": req.wallet, "detail": req.timeframe_detail}
        base = req.base
        if req.from_run:
            rec = store.get(req.from_run)
            if rec is None:
                raise HTTPException(404, "beh neexistuje")
            params = rec["params"]
            settings = rec.get("settings", {})
            strategy = strategy_of(rec)
            instrument = instrument or instrument_for_pair(settings["pair"])
            # beh vie všetko, čo profil potrebuje — čo prišlo v requeste, má prednosť
            for key, src in (("timeframe", "timeframe"), ("timerange", "timerange"),
                             ("fee", "fee"), ("wallet", "wallet"), ("detail", "timeframe_detail")):
                setup[key] = setup[key] if setup[key] is not None else settings.get(src)
            base = base or settings.get("profile")
            popis = f"z behu {req.from_run} ({settings.get('pair')}, {settings.get('timerange')})"
            comment = f"{comment} — {popis}" if comment else popis
        if params is None:
            raise HTTPException(422, "chýbajú parametre: pošli `from_run` alebo `params`")
        # vypnutý 1m detail je tiež informácia, nie „nič" — ulož ho ako false
        setup["detail"] = setup["detail"] or False
        if not instrument:
            raise HTTPException(422, "chýba `instrument` profilu")
        try:
            if strategy not in STRATEGIES:
                raise HTTPException(422, f"neznáma stratégia {strategy!r}")
            user_profiles.save(req.name, params, instrument, comment=comment,
                               title=req.note or None, base=base, settings=setup,
                               overwrite=req.overwrite, strategy=strategy)
        except FileExistsError as exc:
            raise HTTPException(409, str(exc))
        except (user_profiles.ProfileError, ConfigError) as exc:
            raise HTTPException(422, str(exc))
        return {"name": req.name.strip(), **profiles_list(strategy)}

    @app.patch("/api/profiles/{name}")
    def profile_rename(name: str, req: ProfileRenameRequest, strategy: str = Query("ibs")):
        try:
            user_profiles.rename(name, req.name)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc))
        except FileExistsError as exc:
            raise HTTPException(409, str(exc))
        except user_profiles.ProfileError as exc:
            raise HTTPException(422, str(exc))
        return {"name": req.name.strip(), **profiles_list(strategy)}

    @app.delete("/api/profiles/{name}")
    def profile_delete(name: str, strategy: str = Query("ibs")):
        try:
            if not user_profiles.delete(name):
                raise HTTPException(404, f"profil {name} neexistuje")
        except user_profiles.ProfileError as exc:
            raise HTTPException(422, str(exc))
        return {"ok": True, **profiles_list(strategy)}

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
        setup = user_profiles.settings_of(name, strategy)
        return {"name": name, "strategy": strategy, "params": params, "instrument": instrument,
                "timeframe": setup.get("timeframe"), "settings": setup,
                "base": user_profiles.base_of(name, strategy),
                "kind": "user" if user_profiles.is_user(name, strategy) else "builtin"}

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
