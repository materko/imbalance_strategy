"""Stránka a metadáta formulára (`/`, `/api/meta`)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from tradebot.strategies import STRATEGIES

from .. import gitsync
from ... import engines
from ..runner import available_pairs
from .common import STATIC, SECONDS_PER_YEAR, asset_version, current_user
from .context import AppContext


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    runner = ctx.runner
    MAX_SWEEP_RUNS = ctx.max_sweep_runs
    strategy_meta = ctx.strategy_meta

    @router.get("/")
    def index():
        # Stránka bez cache a odkazy na skript a štýly s verziou. `no-cache` samo nestačí:
        # prehliadač, ktorý si súbor uložil ešte PREDTÝM, než sme hlavičku pridali, ho
        # považuje za čerstvý podľa vlastnej heuristiky a znova sa nepýta (Chrome to robí,
        # Edge nie). Verzia v URL je iný kľúč cache, takže stará kópia sa nemá ako použiť.
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        v = asset_version()
        html = html.replace('href="/static/app.css"', f'href="/static/app.css?v={v}"')
        html = html.replace('src="/static/app.js"', f'src="/static/app.js?v={v}"')
        return HTMLResponse(html, headers={"Cache-Control": "no-cache, must-revalidate"})

    @router.get("/api/meta")
    def meta():
        pairs = available_pairs()
        by_key = {key: strategy_meta(key) for key in STRATEGIES}
        return {
            # `params`/`defaults`/`profiles`… na najvyššej úrovni = stratégia "ibs" (spätná
            # kompatibilita pre CLI a testy); stránka pracuje so `strategy_meta[key]`.
            **by_key["ibs"],
            "strategies": [spec.public() for spec in STRATEGIES.values()],
            "exchanges": [{"key": e, "title": engines.EXCHANGE_TITLES.get(e, e)}
                          for e in engines.EXCHANGES],
            "default_exchange": engines.DEFAULT_EXCHANGE,
            # Strop mriežky a cena jedného roka behu — stránka z toho poskladá odhad času.
            "max_sweep_runs": MAX_SWEEP_RUNS,
            "sweep_seconds_per_year": SECONDS_PER_YEAR,
            "strategy_meta": by_key,
            "pairs": pairs,
            "user": current_user(),
            "branch": gitsync.branch(),
            "queue": runner.snapshot(),
        }

    return router
