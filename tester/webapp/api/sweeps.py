"""Mriežky behov cez hodnoty parametra (`/api/sweeps`, replay bodu)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from tradebot.core.config import ConfigError
from tradebot.strategies import STRATEGIES, get_spec

from ..batches import strip_tag
from ..runner import check_market_rules
from ..store import strategy_of
from .common import SECONDS_PER_YEAR, clean_user, goal_note, fmt_value
from .context import AppContext
from .models import SweepRequest, ReplayRequest
from .settings import run_settings


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    runner = ctx.runner
    DEFAULTS = ctx.defaults
    MAX_SWEEP_RUNS = ctx.max_sweep_runs


    def _sweep_minutes(points: int, timerange: str) -> int:
        """Hrubý odhad, ako dlho mriežka pobeží — behy idú za sebou, jeden po druhom."""
        try:
            a, b = (datetime.strptime(x, "%Y%m%d") for x in timerange.split("-"))
        except ValueError:
            return 0
        years = max((b - a).days, 1) / 365.0
        return max(1, round(points * years * SECONDS_PER_YEAR / 60))

    def _point_note(point: dict[str, Any]) -> str:
        return ", ".join(f"{k}={fmt_value(v)}" for k, v in point.items())

    @router.post("/api/sweeps")
    def sweep_start(req: SweepRequest):
        """Rozbalí mriežku a zaradí každý bod ako samostatný beh s tou istou značkou."""
        from ... import sweep as sweep_mod

        if req.goal not in sweep_mod.GOALS:
            raise HTTPException(422, f"neznáme kritérium {req.goal!r}; "
                                     f"známe: {', '.join(sweep_mod.GOALS)}")
        defaults = DEFAULTS.get(req.strategy) or DEFAULTS["ibs"]
        space = {}
        for name, spec in req.space.items():
            if name not in defaults:
                raise HTTPException(422, f"neznámy parameter {name!r}")
            try:
                values = sweep_mod.parse_values(spec)
            except ValueError as exc:
                raise HTTPException(422, f"{name}: {exc}")
            if not values:
                raise HTTPException(422, f"{name}: žiadne hodnoty")
            space[name] = values
        if not space:
            raise HTTPException(422, "sweep potrebuje aspoň jeden parameter")

        points = sweep_mod.expand(space)
        minutes = _sweep_minutes(len(points), req.timerange)
        if MAX_SWEEP_RUNS and len(points) > MAX_SWEEP_RUNS:
            raise HTTPException(422, (
                f"mriežka má {len(points)} behov (odhadom {minutes} min), strop je {MAX_SWEEP_RUNS} — "
                "zúž rozsah alebo krok; strop sa dá zdvihnúť premennou TRADEBOT_MAX_SWEEP_RUNS"))

        # Celá mriežka sa overí ešte pred zaradením: keby prvý bod prešiel a piaty mal
        # hodnotu mimo Pine rozsahu, tester by mal vo fronte štyri behy a chybu k tomu.
        config_cls = get_spec(req.strategy).config_cls
        for point in points:
            merged = {**req.params, **point}
            try:
                config_cls.from_dict({k: v for k, v in merged.items() if not k.startswith("_")})
                check_market_rules(req.pair, merged)
            except (ConfigError, ValueError) as exc:
                raise HTTPException(422, f"bod {_point_note(point)}: {exc}")

        base = run_settings(req)
        # Kým mriežka čaká vo fronte, nič sa v tabuľke nedeje — a tester klikne znova.
        # Rovnaké zadanie preto odmietneme a povieme, kde ho má hľadať.
        podpis = json.dumps([base, points], sort_keys=True, default=str)
        for job in runner.snapshot():
            tag = (job.get("settings") or {}).get("sweep") or {}
            if tag.get("signature") == podpis:
                raise HTTPException(409, (
                    f"tá istá mriežka už čaká vo fronte ({tag['id']}) — nedokončené body "
                    "sa dopočítavajú, výsledky pribúdajú v tabuľke. Zruš ich vo fronte, "
                    "ak si to rozmyslel."))
        # Sekunda nestačí: dva sweepy spustené rýchlo za sebou by mali tú istú značku
        # a v tabuľke by sa zliali do jednej mriežky.
        sweep_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
        goal_note = sweep_mod.describe(req.goal, req.max_dd, req.min_trades)
        ids = []
        for point in points:
            settings = {**base, "sweep": {"id": sweep_id, "values": point, "goal": req.goal,
                                          "max_dd": req.max_dd, "min_trades": req.min_trades,
                                          "points": len(points),
                                          # `min_trades` je za rok; mriežky bez tejto
                                          # značky vznikli s absolútnym významom
                                          "per_year": True, "signature": podpis}}
            note = f"sweep {sweep_id}: {_point_note(point)}" + (f" — {req.note}" if req.note else "")
            try:
                job = runner.submit({**req.params, **point}, settings, note=note,
                                    user=clean_user(req.user))
            except (ConfigError, ValueError) as exc:  # sieť pod sieťou, keby overenie niečo minulo
                raise HTTPException(422, f"bod {_point_note(point)}: {exc}")
            ids.append(job.id)
        return {"id": sweep_id, "runs": ids, "points": len(points), "goal": req.goal,
                "goal_note": goal_note, "minutes": minutes}

    @router.get("/api/sweeps")
    def sweeps_list(limit: int = 50, strategy: str | None = None):
        """Mriežky z histórie, od najnovšej; `strategy` obmedzí na jednu stratégiu.

        Body sú v `sweeps/sweep-<id>.json` (do histórie behov nejdú), staré mriežky ešte
        v histórii; `store.tagged` spojí oboje a fronta pridá body, ktoré len bežia.
        Súbory sú v gite, takže zoznam prežije reštart aj `git pull` cudzích mriežok.

        Filter podľa stratégie nie je pohodlie: parametre sú v každej stratégii iné,
        takže mriežka cez `rrRatio` nemá v ponuke pre Donchian breakout čo robiť.
        """
        if strategy is not None and strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        from ... import sweep as sweep_mod

        skupiny: dict[str, dict[str, Any]] = {}
        for rec in list(store.tagged("sweep")) + list(runner.snapshot()):
            tag = (rec.get("settings") or {}).get("sweep") or {}
            sweep_id = tag.get("id")
            if not sweep_id or (strategy is not None and strategy_of(rec) != strategy):
                continue
            nastavenia = rec["settings"]
            polozka = skupiny.setdefault(sweep_id, {
                "id": sweep_id,
                "goal": tag.get("goal") or "break_even",
                "goal_note": sweep_mod.describe(tag.get("goal") or "break_even",
                                                tag.get("max_dd"), tag.get("min_trades")),
                "params": list(tag.get("values") or {}),
                "pair": nastavenia.get("pair"),
                "timeframe": nastavenia.get("timeframe"),
                "timerange": nastavenia.get("timerange"),
                "strategy": strategy_of(rec),
                "user": rec.get("user") or "",
                "done": 0, "pending": 0,
            })
            if rec.get("status") in ("queued", "running"):
                polozka["pending"] += 1
            else:
                polozka["done"] += 1
        rad = sorted(skupiny.values(), key=lambda x: x["id"], reverse=True)
        return {"total": len(rad), "sweeps": rad[:limit]}

    @router.get("/api/sweeps/{sweep_id}")
    def sweep_detail(sweep_id: str):
        """Stav a poradie mriežky — vidno ju od zaradenia, nie až od prvého výsledku."""
        from ... import sweep as sweep_mod

        fronta = runner.snapshot()
        zive = {j["id"] for j in fronta}
        records = [r for r in store.tagged("sweep", sweep_id) if r["id"] not in zive]
        live = [j for j in fronta
                if (j.get("settings", {}).get("sweep") or {}).get("id") == sweep_id]
        if not records and not live:
            raise HTTPException(404, "taký sweep v histórii nie je")

        tag = (records or live)[0]["settings"]["sweep"]
        ranked = sweep_mod.rank(records, tag.get("goal") or "break_even",
                                max_dd=tag.get("max_dd"), min_trades=tag.get("min_trades"),
                                per_year=bool(tag.get("per_year")))
        names = list(tag.get("values") or {})
        prazdny = dict.fromkeys(
            ("trades", "pnl_pct", "winrate", "max_drawdown_pct", "break_even_pct"))

        # Koľko cudzích behov je pred prvým bodom tejto mriežky. Bez toho vyzerá čakanie
        # ako zaseknutá appka — pritom pred ňou môže stáť iná mriežka.
        prve = next((i for i, j in enumerate(fronta) if j in live), None)
        pred = 0 if prve is None else sum(1 for j in fronta[:prve] if j not in live)
        bezi = next((j for j in live if j.get("status") == "running"), None)

        return {
            "id": sweep_id,
            "goal": tag.get("goal"),
            "goal_note": sweep_mod.describe(tag.get("goal") or "break_even",
                                            tag.get("max_dd"), tag.get("min_trades")),
            "params": names,
            "done": len(records),
            "running": len(live),
            # Beh medzi „dobehol" a „uložený" nie je ani vo fronte, ani v sklade — bez
            # celkového počtu by stav na chvíľu tvrdil „hotových 1 z 1" pri dvoch bodoch.
            "total": max(int(tag.get("points") or 0), len(records) + len(live)),
            "ahead": pred,
            "running_values": (bezi or {}).get("settings", {}).get("sweep", {}).get("values"),
            "rows": [{
                "id": r["id"],
                "values": r["settings"]["sweep"]["values"],
                "status": r.get("status"),
                "ok": r["sweep_ok"],
                "why": r["sweep_why"],
                # bod bez behu v histórii sa otvára prehraním (`/api/points/<id>/replay`)
                "in_history": "batch" not in r,
                "result": {k: (r.get("result") or {}).get(k) for k in prazdny},
            } for r in ranked] + [{
                "id": j["id"],
                "values": j["settings"]["sweep"]["values"],
                "status": j.get("status"),
                "ok": True,
                "why": "",
                "result": dict(prazdny),
            } for j in live],
        }

    @router.post("/api/sweeps/{sweep_id}/cancel")
    def sweep_cancel(sweep_id: str):
        """Zruší všetky nedobehnuté body mriežky naraz.

        Toto je náhrada za strop na veľkosť: preklep v kroku sa opraví jedným klikom
        namiesto toho, aby sa mriežky zhora orezávali.
        """
        ids = [j["id"] for j in runner.snapshot()
               if (j.get("settings", {}).get("sweep") or {}).get("id") == sweep_id]
        if not ids:
            raise HTTPException(404, "z tejto mriežky už nič nebeží ani nečaká")
        return {"cancelled": sum(1 for i in ids if runner.cancel(i))}

    @router.post("/api/points/{run_id}/replay")
    def point_replay(run_id: str, req: ReplayRequest | None = None):
        """Bod mriežky / bunku matice / overenie prehrá ako obyčajný beh — ten do histórie ide.

        Bod nesie celý config, takže beh je ten istý; dostane nové id a poznámku, odkiaľ je.
        """
        rec = store.find(run_id)
        if rec is None:
            raise HTTPException(404, "taký bod ani beh nie je")
        batch = rec.get("batch") or {}
        settings = strip_tag(dict(rec.get("settings") or {}))
        povod = f"{batch.get('kind')} {batch.get('id')}" if batch else f"beh {run_id}"
        note = f"prehratý bod ({povod}): {rec.get('note') or ''}".strip()
        try:
            job = runner.submit(rec.get("params") or {}, settings, note=note[:500],
                                user=clean_user(req.user if req else None))
        except (ConfigError, ValueError, KeyError) as exc:
            raise HTTPException(422, f"bod sa prehrať nedá: {exc}")
        return {**job.public(), "source": run_id}

    return router
