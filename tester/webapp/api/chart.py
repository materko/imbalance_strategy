"""Graf behu, sviečky a Monte Carlo (`/api/runs/{id}/chart`, `/api/candles`)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from .. import chart as chart_data
from ... import montecarlo
from .common import montecarlo_cached
from .context import AppContext


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    replayer = ctx.replayer
    chart_state = ctx.chart_state

    @router.get("/api/runs/{run_id}/chart")
    def run_chart(run_id: str, start: int | None = Query(None, alias="from"),
                  end: int | None = Query(None, alias="to")):
        """Kresby enginu z behu, orezané na okno `from`–`to` (ms epoch).

        Kresby nie sú v gite: keď lokálne nie sú, odpoveď je 409 so stavom a stránka si
        vypýta prepočet (`POST .../chart`)."""
        rec = store.get(run_id)
        if rec is None:
            raise HTTPException(404, "beh neexistuje")
        data = store.drawings(run_id)
        if data is None:
            return JSONResponse({"detail": "graf sa ešte nepočítal", "chart": chart_state(rec)},
                                status_code=409)
        objects = data["objects"] if start is None or end is None else chart_data.window(data, start, end)
        stav = chart_state(rec)
        return {"meta": chart_data.summary(data), "objects": objects,
                "warning": stav.get("warning"), "source": stav.get("source")}

    @router.post("/api/runs/{run_id}/chart")
    def run_chart_replay(run_id: str):
        """Zaradí prepočet kresieb z uloženého configu (na pozadí) a vráti stav."""
        rec = store.get(run_id)
        if rec is None:
            raise HTTPException(404, "beh neexistuje")
        stav = chart_state(rec)
        if stav["state"] == "unavailable":
            raise HTTPException(422, "tento beh graf nemá (nedobehol alebo je to hyperopt)")
        return replayer.request(run_id)

    @router.get("/api/runs/{run_id}/chart/status")
    def run_chart_status(run_id: str):
        rec = store.get(run_id)
        if rec is None:
            raise HTTPException(404, "beh neexistuje")
        return chart_state(rec)

    @router.get("/api/candles")
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

    @router.get("/api/runs/{run_id}/montecarlo")
    def run_montecarlo(run_id: str, fee: float | None = None, account: float | None = None,
                       risk: float | None = None, risk_pct: float | None = None,
                       block: int = montecarlo.DEFAULT_BLOCK,
                       iterations: int = 10_000, seed: int = 0):
        """Bootstrap nad obchodmi behu — interval okolo výsledku a riziko účtu.

        Ráta sa až na vyžiadanie (rozbalenie sekcie v detaile), lebo pri behu s
        tisíckami obchodov to trvá jednotky sekúnd. Beh je nemenný, takže sa
        výsledok pamätá.
        """
        rec = store.get(run_id)
        if rec is None:
            raise HTTPException(404, "beh neexistuje")
        trades = store.trades(run_id)
        if not trades:
            raise HTTPException(422, "beh nemá obchody, nie je čo premiešavať")
        settings = rec.get("settings") or {}
        risk_ref = montecarlo.sizing_of(rec)
        opts = {
            "fee_pct": fee if fee is not None else float(settings.get("fee") or 0.0) * 100.0,
            "account": account if account else float(settings.get("wallet") or 10_000.0),
            "risk_ref": risk_ref,
            "risk": risk if risk else risk_ref,
            "risk_pct": risk_pct or None,
            "block": max(1, min(int(block), 200)),
            "iterations": max(200, min(int(iterations), 50_000)),
            "seed": int(seed),
        }
        return montecarlo_cached(run_id, trades, opts)

    return router
