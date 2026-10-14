"""Stránka a metadáta formulára (`/`, `/api/meta`)."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from tradebot.strategies import STRATEGIES

from .. import gitsync, profiles as user_profiles
from ... import engines
from ..runner import available_pairs
from .common import STATIC, SECONDS_PER_YEAR, asset_version, current_user
from .context import AppContext


#: Prefixy profilov, ktoré prešli smernicou (tie isté ako `SMERNICE_PREFIXES` v settings.js).
#: `PRESIEL_SMERNICAMI_` zapisuje ranná úloha na Mac mini (a pri exporte maže, čo sama nevyrobila);
#: `SMERNICE_CS_` sú kópie pre stratégie s C# jadrom (ibsentrynet, vwaporbnet, vwapadxnet) — vlastný
#: prefix, aby ich ten export nezmazal.
SMERNICE_PREFIXES = ("PRESIEL_SMERNICAMI_", "SMERNICE_CS_")


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
        html = re.sub(r'src="(/static/js/[^"?]+\.js)"', lambda m: f'src="{m.group(1)}?v={v}"', html)
        return HTMLResponse(html, headers={"Cache-Control": "no-cache, must-revalidate"})

    @router.get("/api/strategies/{key}/meta")
    def strategy_meta_one(key: str, v: str = ""):
        """Metadáta formulára jednej stratégie: parametre, defaulty a profily (aj vlastné) a ich
        `version`. Stránka sa pýta pri každom prepnutí stratégie a posiela verziu, ktorú má
        (`?v=`); keď sa nič nezmenilo, dostane len `{"unchanged": true}` a nič sa neskladá."""
        from tradebot.strategies import canonical_key

        k = canonical_key(key) or ""
        if k not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {key!r}")
        version = ctx.strategy_meta_version(k)
        if v and v == version:
            return {"strategy": k, "version": version, "unchanged": True}
        return {"strategy": k, "version": version, **strategy_meta(k)}

    @router.get("/api/strategies/{key}/explainer")
    def explainer(key: str):
        """Vysvetlivka stratégie pre laika (Markdown) — okno „Ako funguje?" vo formulári."""
        from tradebot.strategies import canonical_key

        spec = STRATEGIES.get(canonical_key(key) or "")
        if spec is None:
            raise HTTPException(404, f"neznáma stratégia {key!r}")
        return {"key": spec.key, "title": spec.title, "markdown": spec.explainer()}

    @router.get("/api/meta")
    def meta():
        pairs = available_pairs()
        # Parametre a profily stratégií sa tu neposielajú (stovky profilov × desiatky stratégií
        # = sekundy a megabajty pri každom načítaní) — stránka si ich vypýta cez
        # `/api/strategies/<key>/meta` až pri výbere stratégie; tu je len zoznam a strom.
        return {
            # `params`/`defaults`/`profiles`… na najvyššej úrovni = stratégia "ibs" (spätná
            # kompatibilita pre CLI a testy); stránka pracuje so `strategy_meta[key]`.
            **strategy_meta("ibs"),
            # Stratégie s profilom, ktorý prešiel smernicou — priečinok SMERNICE vo výbere stratégie.
            "smernice_strategies": user_profiles.strategies_with_prefix(SMERNICE_PREFIXES),
            "strategies": [spec.public() for spec in STRATEGIES.values()],
            "exchanges": [{"key": e, "title": engines.EXCHANGE_TITLES.get(e, e)}
                          for e in engines.EXCHANGES],
            "default_exchange": engines.DEFAULT_EXCHANGE,
            # Strop mriežky a cena jedného roka behu — stránka z toho poskladá odhad času.
            "max_sweep_runs": MAX_SWEEP_RUNS,
            "sweep_seconds_per_year": SECONDS_PER_YEAR,
            "pairs": pairs,
            "user": current_user(),
            "branch": gitsync.branch(),
            "queue": runner.snapshot(),
        }

    return router
