"""Matice trhov (`/api/matri*`)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from tradebot.core.config import ConfigError
from tradebot.strategies import STRATEGIES

from ... import engines
from ..runner import available_pairs
from ..store import strategy_of
from .common import clean_user, goal_note
from .context import AppContext
from .models import MatrixRequest
from .settings import run_settings


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    runner = ctx.runner

    @router.get("/api/matrix/meta")
    def matrix_meta(wallet: float = 10000, timeframe: str = "3m", strategy: str = "ibs"):
        """Čo o matici treba vedieť dopredu: kde sa jeden kontrakt nezmestí do peňaženky."""
        from ... import matrix as mx

        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        pary = [p["pair"] for p in available_pairs()]
        male = mx.wallet_check(pary, float(wallet), timeframe=timeframe)
        return {"pairs": pary, "small_wallet": male,
                "suggested_wallet": round(max(male.values()) * 2) if male else None}

    @router.post("/api/matrices")
    def matrix_start(req: MatrixRequest):
        """Zaradí každú bunku matice ako obyčajný beh s tou istou značkou."""
        from ... import matrix as mx

        znama = {p["pair"] for p in available_pairs()}
        nezname = [p for p in req.pairs if p not in znama]
        if nezname:
            raise HTTPException(422, f"neznáme páry: {', '.join(nezname)}")
        try:
            bunky = mx.expand(req.pairs, req.timeframes)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

        params = dict(req.params)
        prepocet: list[str] = []
        if req.relative:
            params, prepocet = mx.to_relative(
                params, strategy=req.strategy, ref_pair=req.pair,
                ref_timeframe=req.timeframe, timerange=req.timerange)

        bunky, preskocene = mx.playable(
            bunky, exchange=req.exchange or engines.DEFAULT_EXCHANGE,
            engine=req.engine, params=params)
        if not bunky:
            raise HTTPException(422, "žiadna bunka matice sa spustiť nedá: "
                                     + "; ".join(f"{k}: {v}" for k, v in preskocene.items()))

        base = run_settings(req)
        matrix_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
        ids = []
        for cell in bunky:
            settings = {**base, "pair": cell.pair, "timeframe": cell.timeframe,
                        "matrix": {"id": matrix_id, "pair": cell.pair,
                                   "timeframe": cell.timeframe, "goal": req.goal,
                                   "relative": bool(req.relative),
                                   "min_trades": req.min_trades, "cells": len(bunky)}}
            note = (f"matica {matrix_id}: {cell.pair} {cell.timeframe}"
                    + (f" — {req.note}" if req.note else ""))
            try:
                job = runner.submit(params, settings, note=note, user=clean_user(req.user))
            except (ConfigError, ValueError) as exc:
                preskocene[cell.key] = str(exc)
                continue
            ids.append(job.id)
        if not ids:
            raise HTTPException(422, "žiadna bunka sa nezaradila: "
                                     + "; ".join(f"{k}: {v}" for k, v in preskocene.items()))
        return {"id": matrix_id, "runs": ids, "cells": len(ids), "skipped": preskocene,
                "converted": prepocet,
                "wallet_small": mx.wallet_check([c.pair for c in bunky],
                                                float(req.wallet or 10000),
                                                timeframe=req.timeframes[0])}

    @router.get("/api/matrices")
    def matrices_list(limit: int = 50, strategy: str | None = None):
        """Matice z histórie, od najnovšej."""
        if strategy is not None and strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        skupiny: dict[str, dict[str, Any]] = {}
        for rec in list(store.tagged("matrix")) + list(runner.snapshot()):
            tag = (rec.get("settings") or {}).get("matrix") or {}
            if not tag.get("id"):
                continue
            if strategy is not None and strategy_of(rec) != strategy:
                continue
            polozka = skupiny.setdefault(tag["id"], {
                "id": tag["id"], "strategy": strategy_of(rec),
                "timerange": rec["settings"].get("timerange"),
                "goal": tag.get("goal"), "relative": tag.get("relative"),
                "pairs": set(), "timeframes": set(), "done": 0, "pending": 0,
                "user": rec.get("user") or "",
            })
            polozka["pairs"].add(rec["settings"].get("pair"))
            polozka["timeframes"].add(rec["settings"].get("timeframe"))
            if rec.get("status") in ("queued", "running"):
                polozka["pending"] += 1
            else:
                polozka["done"] += 1
        rad = []
        for p in sorted(skupiny.values(), key=lambda x: x["id"], reverse=True)[:limit]:
            rad.append({**p, "pairs": sorted(x for x in p["pairs"] if x),
                        "timeframes": sorted(x for x in p["timeframes"] if x)})
        return {"total": len(skupiny), "matrices": rad}

    @router.get("/api/matrices/{matrix_id}")
    def matrix_detail(matrix_id: str):
        """Tabuľka `trh × timeframe` a verdikt — aj kým sa dopočítava."""
        from ... import matrix as mx

        live = [j for j in runner.snapshot()
                if ((j.get("settings", {}).get("matrix") or {}).get("id")) == matrix_id]
        zive = {j["id"] for j in live}
        zaznamy = [r for r in store.tagged("matrix", matrix_id) if r["id"] not in zive]
        if not zaznamy and not live:
            raise HTTPException(404, "taká matica v histórii nie je")

        tag = (zaznamy or live)[0]["settings"]["matrix"]
        goal = tag.get("goal") or "break_even"
        poradie = mx.rank(zaznamy, goal, min_trades=tag.get("min_trades") or mx.MIN_TRADES)
        tabulka = mx.matrix(poradie + [{
            "id": j["id"], "status": j.get("status"), "settings": j["settings"], "result": {},
        } for j in live])
        return {
            "id": matrix_id,
            "goal": goal,
            "goal_note": goal_note(goal, None, tag.get("min_trades")),
            "relative": bool(tag.get("relative")),
            "timerange": (zaznamy or live)[0]["settings"].get("timerange"),
            "done": len(zaznamy),
            "pending": len(live),
            "total": max(int(tag.get("cells") or 0), len(zaznamy) + len(live)),
            "table": tabulka,
            "verdict": mx.verdict(zaznamy) if zaznamy else "",
            "best": [{"pair": r["settings"]["pair"], "timeframe": r["settings"].get("timeframe"),
                      "id": r["id"], "ok": r["sweep_ok"], "why": r["sweep_why"],
                      "result": {k: (r.get("result") or {}).get(k) for k in
                                 ("trades", "pnl_pct", "winrate", "max_drawdown_pct",
                                  "break_even_pct")}}
                     for r in poradie[:12]],
        }

    return router
