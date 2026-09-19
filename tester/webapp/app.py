"""FastAPI aplikácia — REST API nad `store`, `runner` a `gitsync` + statická stránka.

    python -m tester.webapp                    # 127.0.0.1:8765
    TRADEBOT_WEB_HOST=0.0.0.0 TRADEBOT_WEB_PORT=8765  # v Dockeri

Žiadne prihlásenie: aplikácia je určená na lokálne spustenie (alebo za reverse
proxy s vlastnou autentifikáciou). Meno testera si tester nastaví v hlavičke
stránky (drží sa v prehliadači) a posiela sa s každým behom aj s Push; predvolené
je `TRADEBOT_USER`, inak `git config user.name`.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import chart as chart_data  # noqa: F401 — testy ho podvrhujú cez `app_mod.chart_data`
from .. import engines  # noqa: F401 — testy ho podvrhujú cez `app_mod.engines`
from .anstore import AnalyticsStore
from .api import (
    analytics, analytics_history, analytics_prepare, chart, git, hub, hyperopt, matrix, meta,
    profiles, prop_paper, runs, sweeps,
)
from .api.common import (  # noqa: F401 — verejné mená modulu z čias pred rozdelením
    _MC_CACHE, STATIC, current_user, default_timerange, montecarlo_cached,
)
from .api.context import AppContext
from .replay import ChartReplayer
from .runner import BacktestRunner
from .store import RunStore

#: Poradie registrácie routov; `/static` sa pripája až za nimi.
ROUTERS = (meta, profiles, runs, sweeps, hyperopt, analytics, analytics_prepare,
           analytics_history, prop_paper, matrix, hub, chart, git)


class _NoCacheStatic(StaticFiles):
    """Stránka a skript sa po aktualizácii nesmú ťahať z cache prehliadača.

    Bez toho tester po `git pull` a reštarte vidí starú stránku (a nové pole jednoducho
    chýba), kým si nespraví hard refresh. Súbory sú lokálne a malé, takže revalidácia
    pri každom načítaní nič nestojí.
    """

    def is_not_modified(self, response_headers, request_headers) -> bool:  # noqa: D102
        return False

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


def create_app(store: RunStore | None = None, runner: BacktestRunner | None = None,
               replayer: ChartReplayer | None = None) -> FastAPI:
    store = store or RunStore()
    anstore = AnalyticsStore()
    runner = runner or BacktestRunner(store)
    #: Prepočet grafov má vlastné vlákno — graf otvorený počas mriežky nečaká na frontu.
    replayer = replayer or ChartReplayer(store)
    app = FastAPI(title="TradeBot backtest webapp", version="0.2")
    app.state.store = store
    app.state.runner = runner
    app.state.replayer = replayer
    ctx = AppContext(app, store, runner, replayer, anstore)
    for module in ROUTERS:
        app.include_router(module.build(ctx))
    app.mount("/static", _NoCacheStatic(directory=str(STATIC)), name="static")
    return app


app = create_app()
