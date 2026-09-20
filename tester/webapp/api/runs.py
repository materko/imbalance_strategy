"""Behy a fronta: zadanie, zoznam, detail, log, profil, zmazanie (`/api/runs`, `/api/queue`)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from tradebot.core.config import ConfigError
from tradebot.strategies import get_spec

from ..runner import instrument_for_pair
from ..store import strategy_of, summarize_for_list
from .common import clean_user
from .context import AppContext
from .models import RunRequest
from .settings import run_settings


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    runner = ctx.runner
    defaults_of = ctx.defaults_of
    chart_state = ctx.chart_state

    #: Nad toľko riadkov sa série starých behov nedopočítavajú — je to čítanie
    #: `trades.json` behu po behu (~5 ms na beh) a stránka histórie má 50 riadkov.
    STREAK_FILL_LIMIT = 200

    @router.get("/api/runs")
    def runs(q: str = "", limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0)):
        recs = store.search(q) if q.strip() else store.all()
        vybrane = recs[offset:offset + limit]
        rows = [summarize_for_list(r, defaults_of(r)) for r in vybrane]
        # Beh spred sérií ich v `run.json` nemá; na stránke histórie sa dopočítajú
        # z obchodov (natrvalo ich dopíše `cli recompute --write`).
        if len(rows) <= STREAK_FILL_LIMIT:
            from tradebot.core.money import streaks

            for row, rec in zip(rows, vybrane):
                vysledok = row["result"]
                if vysledok.get("trades") and not vysledok.get("streaks"):
                    vysledok["streaks"] = streaks(store.trades(rec["id"]))
        return {"total": len(recs), "runs": rows}

    @router.post("/api/runs")
    def submit(req: RunRequest):
        settings = run_settings(req)
        try:
            job = runner.submit(req.params, settings, note=req.note, user=clean_user(req.user))
        except (ConfigError, ValueError) as exc:
            raise HTTPException(422, str(exc))
        return job.public()

    @router.get("/api/queue")
    def queue():
        return runner.snapshot()

    @router.post("/api/queue/{job_id}/cancel")
    def cancel(job_id: str):
        if not runner.cancel(job_id):
            raise HTTPException(404, "beh nie je vo fronte ani nebeží")
        return {"ok": True}

    @router.get("/api/runs/{run_id}")
    def run(run_id: str):
        rec = store.get(run_id)
        if rec is None:
            # Bod celku (mriežka, matica, overenie) — v histórii nie je, ale CLI naň čaká
            # rovnako ako na beh, tak dostane jeho výsledok.
            bod = store.batches.find(run_id)
            if bod is not None:
                return {"record": bod, "trades": [], "live": False, "batch": bod["batch"]}
            job = runner.job(run_id)
            if job is None:
                raise HTTPException(404, "beh neexistuje")
            return {"record": job.public(), "trades": [], "live": True}
        defaults = defaults_of(rec)
        rec["overrides"] = {k: v for k, v in rec.get("params", {}).items()
                            if not k.startswith("_") and defaults.get(k) != v}
        # Starší beh (spred úplného záznamu configu, alebo spred pridania poľa) tieto
        # polia nemá — profil z neho ich doplní dnešnými defaultmi a detail to povie.
        rec["missing_params"] = sorted(set(defaults) - set(rec.get("params") or {}))
        rec["chart"] = chart_state(rec)
        rec["has_chart"] = rec["chart"]["state"] == "ready"
        trades = store.trades(run_id)
        # Beh spred sérií ich v súhrne nemá — dopočítajú sa z obchodov tým istým vzorcom
        # ako pri novom behu (do `run.json` ich zapíše až `cli recompute`).
        if trades and not (rec.get("result") or {}).get("streaks"):
            from tradebot.core.money import streaks

            # kópia: `store.get` vracia plytkú kópiu, do cache tento dopočet nepatrí
            rec["result"] = {**(rec.get("result") or {}), "streaks": streaks(trades)}
        return {"record": rec, "trades": trades, "live": False}

    @router.get("/api/runs/{run_id}/log", response_class=PlainTextResponse)
    def run_log(run_id: str):
        job = runner.job(run_id)
        if job is not None and job.status in ("queued", "running"):
            return "\n".join(job.log_lines[-400:])
        return store.log(run_id)

    @router.get("/api/runs/{run_id}/profile.json")
    def run_profile(run_id: str):
        rec = store.get(run_id)
        if rec is None:
            raise HTTPException(404, "beh neexistuje")
        strategy = strategy_of(rec)
        try:
            # celý config, nie len to, čo beh zapísal — starší beh doplnia defaulty
            config = get_spec(strategy).config_cls.from_dict(
                {k: v for k, v in (rec.get("params") or {}).items() if not k.startswith("_")}).to_dict()
        except ConfigError as exc:
            raise HTTPException(422, f"parametre behu už config neprijme: {exc}")
        params = {
            "_comment": [f"profil z behu {run_id} ({rec.get('settings', {}).get('pair')}, "
                         f"{rec.get('settings', {}).get('timerange')}) - export z webapp"],
            "_strategy": strategy,
            "_instrument": instrument_for_pair(rec["settings"]["pair"]),
            **config,
        }
        return JSONResponse(params, headers={"Content-Disposition": f'attachment; filename="{run_id}.json"'})

    @router.delete("/api/runs/{run_id}")
    def delete(run_id: str):
        if not store.delete(run_id):
            raise HTTPException(404, "beh neexistuje")
        return {"ok": True}

    return router
