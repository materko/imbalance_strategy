"""Hyperopt a okolie víťaza (`/api/hyperopt*`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from tradebot.core.config import ConfigError
from tradebot.strategies import STRATEGIES, get_spec

from ..batches import strip_tag
from ..store import strategy_of
from .common import clean_user, plateau_note, goal_note
from .context import AppContext
from .models import HyperoptRequest
from .settings import run_settings


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    runner = ctx.runner
    DEFAULTS = ctx.defaults

    @router.get("/api/hyperopt/meta")
    def hyperopt_meta(strategy: str = "ibs"):
        """Čo o ladení vie stratégia — odporúčaný priestor a varovania.

        Vedomosť je pri stratégii (`hyperopt_cls`), nie v appke; stránka ju len ukáže.
        """
        from ... import hyperopt as ho

        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        znalosti = ho.knowledge_note(strategy)
        return {"strategy": strategy, "note": znalosti,
                "suggested": ho.suggested(strategy),
                "warn": dict(ho.knowledge(get_spec(strategy)).WARN),
                "windows": list(ho.REFERENCE_WINDOWS),
                "default_epochs": ho.DEFAULT_EPOCHS}

    @router.post("/api/hyperopts")
    def hyperopt_start(req: HyperoptRequest):
        """Zaradí hyperopt do tej istej fronty ako backtesty — vyťaží všetky jadrá."""
        from ... import hyperopt as ho

        if not req.space:
            raise HTTPException(422, "hyperopt potrebuje aspoň jeden parameter")
        defaults = DEFAULTS.get(req.strategy) or DEFAULTS["ibs"]
        for name in req.space:
            if name not in defaults:
                raise HTTPException(422, f"neznámy parameter {name!r}")
        try:
            plan = ho.build_plan(req.space, strategy=req.strategy, goal=req.goal,
                                 max_dd=req.max_dd, min_trades=req.min_trades, note=req.note)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

        base = run_settings(req)
        # Dvesto epoch s peňaženkou, do ktorej sa nezmestí ani jeden kontrakt, je dvesto
        # riadkov núl: engine dá signály a Freqtrade každý vstup odmietne. Break-even od
        # peňaženky nezávisí, takže ju zvýšiť sa smie — a treba to povedať skôr, než to beží.
        from ... import matrix as mx

        male = mx.wallet_check([req.pair], float(req.wallet or 0), timeframe=req.timeframe,
                               timerange=req.timerange)
        if male:
            nominal = male[req.pair]
            cislo = lambda v: f"{v:,.0f}".replace(",", " ")  # noqa: E731
            raise HTTPException(422, (
                f"Peňaženka {cislo(req.wallet)} je na {req.pair} malá: jeden kontrakt má nominál "
                f"~{cislo(nominal)}, takže Freqtrade odmietne každý vstup a všetky epochy by mali "
                f"nula obchodov. Zvýš peňaženku aspoň na {cislo(nominal * 2)} — break-even od nej "
                f"nezávisí."))
        settings = {**base, "hyperopt": {
            "knobs": dict(req.space), "goal": req.goal, "max_dd": req.max_dd,
            "min_trades": req.min_trades, "epochs": req.epochs, "seed": req.seed,
            "verify": req.verify,
        }}
        popis = ", ".join(f"{k}={v}" for k, v in req.space.items())
        note = f"hyperopt {popis}" + (f" — {req.note}" if req.note else "")
        try:
            job = runner.submit(req.params, settings, note=note, user=clean_user(req.user))
        except (ConfigError, ValueError) as exc:
            raise HTTPException(422, str(exc))
        return {"id": job.id, "epochs": req.epochs, "goal": req.goal,
                "goal_note": goal_note(req.goal, req.max_dd, req.min_trades),
                "warn": ho.warnings_for(req.space, req.strategy),
                "knobs": {k.name: (list(k.choices) if k.choices is not None
                                   else {"low": k.low, "high": k.high, "step": k.step})
                          for k in plan.knobs}}

    @router.get("/api/hyperopts")
    def hyperopts_list(limit: int = 50, strategy: str | None = None):
        """Hyperopty z histórie, od najnovšieho; `strategy` obmedzí na jednu stratégiu."""
        if strategy is not None and strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        out = []
        for rec in list(store.all()) + list(runner.snapshot()):
            zadanie = (rec.get("settings") or {}).get("hyperopt") or {}
            if not zadanie.get("knobs"):
                continue
            if strategy is not None and strategy_of(rec) != strategy:
                continue
            nastavenia = rec["settings"]
            out.append({
                "id": rec["id"],
                "status": rec.get("status"),
                "strategy": strategy_of(rec),
                "params": list(zadanie["knobs"]),
                "goal": zadanie.get("goal"),
                "goal_note": goal_note(zadanie.get("goal") or "break_even",
                                        zadanie.get("max_dd"), zadanie.get("min_trades")),
                "pair": nastavenia.get("pair"),
                "timeframe": nastavenia.get("timeframe"),
                "timerange": nastavenia.get("timerange"),
                "epochs": zadanie.get("epochs"),
                "epochs_done": zadanie.get("epochs_done"),
                "user": rec.get("user") or "",
            })
        out.sort(key=lambda x: x["id"], reverse=True)
        return {"total": len(out), "hyperopts": out[:limit]}

    def _plateau_of(run_id: str, zadanie: dict[str, Any]) -> dict[str, Any] | None:
        """Vyhodnotenie okolia víťaza, keď už nejakí susedia bežali."""
        from ... import plateau as pl

        bezia = [j for j in runner.snapshot()
                 if ((j.get("settings", {}).get("plateau") or {}).get("id")) == run_id]
        zive = {j["id"] for j in bezia}
        susedia = [r for r in store.tagged("plateau", run_id) if r["id"] not in zive]
        if not susedia and not bezia:
            return None
        ladene = [r for r in store.tagged("hyperopt_run", run_id)
                  if (r["settings"].get("hyperopt_run") or {}).get("tuned")]
        if not ladene:
            return {"pending": len(bezia), "rows": [], "verdict": ""}
        vitaz = ladene[0]

        # Interval vitaza z Monte Carla je meradlo, ktorym sa rozhoduje, ci sused "drzi".
        # Starý beh v histórii má obchody; bod v `sweeps/` nesie interval z uloženia.
        interval = pl.winner_ci(vitaz, store.trades(vitaz["id"]) if "batch" not in vitaz else None)
        hodnotenie = pl.assess(vitaz, susedia, interval)
        return {**hodnotenie.to_dict(), "pending": len(bezia), "note": plateau_note()}

    @router.get("/api/hyperopts/{run_id}")
    def hyperopt_detail(run_id: str):
        """Zadanie, epochy, víťaz a overovacie behy na referenčných oknách."""
        from ... import hyperopt as ho

        rec = store.get(run_id)
        if rec is None:
            live = [j for j in runner.snapshot() if j["id"] == run_id]
            if not live:
                raise HTTPException(404, "taký hyperopt v histórii nie je")
            rec = live[0]
        zadanie = (rec.get("settings") or {}).get("hyperopt") or {}
        if not zadanie.get("knobs"):
            raise HTTPException(404, "tento beh nie je hyperopt")

        # Jeden tvar detailu pre webapp aj CLI (`tester.hyperopt.detail`); tu sa len
        # pridajú bežiace overovacie behy a okolie víťaza.
        epochs = store.extra(run_id, "epochs.json") or []
        fronta = [j for j in runner.snapshot()
                  if ((j.get("settings") or {}).get("hyperopt_run") or {}).get("id") == run_id]
        zive = {j["id"] for j in fronta}
        overenia = [r for r in store.tagged("hyperopt_run", run_id) if r["id"] not in zive] + fronta
        try:
            log_text = store.log(run_id) or ""
        except OSError:
            log_text = ""
        return {**ho.detail(rec, epochs, overenia, log_text),
                "plateau": _plateau_of(run_id, zadanie)}

    @router.post("/api/hyperopts/{run_id}/plateau")
    def hyperopt_plateau(run_id: str):
        """Zaradí susedov víťaza — o krok a o dva kroky na každom ladenom parametri.

        Hyperopt vráti jedno číslo a to nehovorí nič o tom, či je stredom niečoho, alebo
        náhodnou dierou v šume. Susedia to rozhodnú.
        """
        from ... import plateau as pl

        rec = store.get(run_id)
        zadanie = ((rec or {}).get("settings") or {}).get("hyperopt") or {}
        if not zadanie.get("knobs"):
            raise HTTPException(404, "taký hyperopt v histórii nie je")
        vitaz_params = zadanie.get("overrides")
        if not vitaz_params:
            raise HTTPException(422, "hyperopt nemá víťaza (žiadna epocha nesplnila mantinely)")

        ladene = [r for r in store.tagged("hyperopt_run", run_id)
                  if (r["settings"].get("hyperopt_run") or {}).get("tuned")]
        if not ladene:
            raise HTTPException(422, "beh víťaza na ladenom okne v histórii nie je "
                                     "(hyperopt bežal bez overenia?)")
        vitaz = ladene[0]

        susedia = pl.neighbours(zadanie["knobs"], vitaz_params)
        if not susedia:
            raise HTTPException(422, "víťaz nemá v rozsahu plánu žiadnych susedov")

        base = strip_tag(vitaz["settings"])
        ids, preskocene = [], {}
        for sused in susedia:
            params = {**(vitaz.get("params") or {}), sused.param: sused.value}
            settings = {**base, "plateau": {"id": run_id, "param": sused.param,
                                            "value": sused.value, "step": sused.step}}
            try:
                job = runner.submit(params, settings,
                                    note=f"okolie {run_id}: {sused.param}={sused.value}",
                                    user=clean_user(None))
            except (ConfigError, ValueError) as exc:
                preskocene[sused.label] = str(exc)
                continue
            ids.append(job.id)
        if not ids:
            raise HTTPException(422, "žiadny sused sa nezaradil: "
                                     + "; ".join(f"{k}: {v}" for k, v in preskocene.items()))
        return {"id": run_id, "runs": ids, "neighbours": len(ids), "skipped": preskocene}

    return router
