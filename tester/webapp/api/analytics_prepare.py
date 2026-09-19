"""Príprava základnej analytiky: plán behov na päť okien (`/api/analytics/prepare`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from tradebot.core.config import ConfigError
from tradebot.core.types import INSTRUMENTS
from tradebot.strategies import STRATEGIES

from .. import chart as chart_data, profiles as user_profiles
from ... import engines
from ..runner import REPO, available_pairs, default_params, instrument_for_pair
from ..store import strategy_of
from .common import clean_user
from .context import AppContext
from .models import RunRequest, AnalyticsPrepareRequest
from .settings import run_settings, TIMERANGE_RE


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store
    runner = ctx.runner

    def _profile_setup(profile: str, strategy: str, engine: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
        """Parametre a nastavenia behu z profilu, ako na karte Nový beh: Pine defaulty
        prepísané profilom; poplatok, peňaženka a 1m detail z vlastného profilu."""
        target: str | Path | None = profile or None
        if profile.endswith(".json"):
            path = (REPO / profile).resolve()
            if not path.is_relative_to(REPO) or not path.exists():
                raise HTTPException(404, f"profil {profile!r} nie je JSON v repozitári")
            target = path
        try:
            params, _ = default_params(target, strategy, engine=engine)
        except (ConfigError, FileNotFoundError) as exc:
            raise HTTPException(404, str(exc))
        # Cesta k JSON (archív profilov) nastavenia behu nemá; vlastný profil áno.
        setup = user_profiles.settings_of(profile, strategy) if profile and not isinstance(target, Path) else {}
        return params, setup

    def _same_config(norm: dict[str, Any], rec: dict[str, Any]) -> bool:
        """Beh má tie isté parametre ako zadanie (obe doplnené Pine defaultmi)."""
        from ... import analytics as an

        other = an.normalized_params(rec)
        return all(norm.get(k) == other.get(k) for k in set(norm) | set(other))

    @router.post("/api/analytics/prepare")
    def analytics_prepare(req: AnalyticsPrepareRequest):
        """Behy pre analytiku profilu na trhu - každé referenčné okno buď **má hotový beh
        v histórii** (tie isté parametre, pár, TF a engine: použije sa, nič sa nepočíta
        znova), alebo sa **zaradí** do fronty. Tester klikne Spočítať a nič iné: nevyberá
        behy z histórie a neklikne „doplniť okná" - analytika je o profile na trhu, nie
        o tom, čo sa kedy náhodou spustilo.

        `dry_run` len povie stav okien (formulár to ukáže pri výbere). Okno mimo dát páru
        je `no_data`; body mriežky a plató sa ako hotové behy neberú (sú to skúšky
        parametra). Beh, ktorý na to isté zadanie už čaká vo fronte, sa nezaradí druhýkrát.
        """
        from ... import analytics as an
        from ... import hyperopt as ho

        strategy = req.strategy
        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        params, setup = _profile_setup(req.profile, strategy, req.engine)
        try:
            inst = INSTRUMENTS[instrument_for_pair(req.pair)]
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        if req.timeframe not in chart_data.available_timeframes(req.pair):
            raise HTTPException(422, f"pre {req.pair} nie sú {req.timeframe} dáta")
        engine = req.engine or engines.default_engine(inst, req.timeframe)
        okna = list(req.windows or ho.REFERENCE_WINDOWS)
        for w in okna:
            if not TIMERANGE_RE.match(w):
                raise HTTPException(422, f"okno {w!r} musí byť YYYYMMDD-YYYYMMDD")
        norm = an.normalized_params({"settings": {"strategy": strategy}, "params": params})
        config_key = an.config_key({"settings": {"strategy": strategy}, "params": params})

        hotove: dict[str, dict[str, Any]] = {}
        for rec in store.all():
            s = rec.get("settings") or {}
            if (strategy_of(rec) != strategy or rec.get("status") != "done"
                    or s.get("pair") != req.pair or s.get("timeframe") != req.timeframe
                    or s.get("timerange") not in okna or (s.get("engine") or engine) != engine
                    or s.get("sweep") or s.get("plateau") or not _same_config(norm, rec)):
                continue
            w = s["timerange"]
            if w not in hotove or rec["id"] > hotove[w]["id"]:
                hotove[w] = rec
        vo_fronte: dict[str, dict[str, Any]] = {}
        for j in runner.snapshot():
            s = j.get("settings") or {}
            job = runner.job(j["id"])
            if (s.get("pair") == req.pair and s.get("timeframe") == req.timeframe
                    and s.get("timerange") in okna and (s.get("strategy") or "ibs") == strategy
                    and (s.get("engine") or engine) == engine and job is not None
                    and _same_config(norm, {"settings": s, "params": job.params})):
                vo_fronte[s["timerange"]] = j
        rozsah = next((p for p in available_pairs() if p["pair"] == req.pair), None) or {}
        od, do = str(rozsah.get("from") or "").replace("-", ""), str(rozsah.get("to") or "").replace("-", "")

        def plan_okien(pair: str, hotove: dict[str, dict[str, Any]], vo_fronte: dict[str, dict[str, Any]],
                       od: str, do: str, poznamka: str, engine: str) -> tuple[list[dict[str, Any]], list[str]]:
            windows, queued = [], []
            for w in okna:
                if w in hotove:
                    rec = hotove[w]
                    windows.append({"window": w, "run_id": rec["id"], "status": "done",
                                    "trades": int((rec.get("result") or {}).get("trades") or 0)})
                elif w in vo_fronte:
                    windows.append({"window": w, "run_id": vo_fronte[w]["id"], "status": vo_fronte[w]["status"]})
                elif od and do and (w[9:] <= od or w[:8] >= do):
                    windows.append({"window": w, "run_id": None, "status": "no_data"})
                elif req.dry_run:
                    windows.append({"window": w, "run_id": None, "status": "missing"})
                else:
                    r = RunRequest(params=params, pair=pair, strategy=strategy, timeframe=req.timeframe,
                                   timerange=w, fee=setup.get("fee"), wallet=setup.get("wallet") or 10000,
                                   timeframe_detail=setup.get("detail", "1m") or None, engine=engine,
                                   profile=req.profile or None,
                                   note=f"analytika: {req.profile or 'Pine defaulty'} · okno {w}{poznamka}",
                                   user=req.user)
                    settings = {**run_settings(r), "checkup": {"analytics": req.profile or "(Pine defaulty)",
                                                                "strategy": strategy}}
                    try:
                        job = runner.submit(r.params, settings, note=r.note, user=clean_user(req.user))
                    except (ConfigError, ValueError) as exc:
                        raise HTTPException(422, f"okno {w}: {exc}")
                    windows.append({"window": w, "run_id": job.id, "status": "queued"})
                    queued.append(job.id)
            return windows, queued

        def suhrn(windows: list[dict[str, Any]], queued: list[str]) -> dict[str, Any]:
            return {
                "windows": windows, "queued": queued,
                "ready": [x["run_id"] for x in windows if x["status"] == "done"],
                "pending": [x["run_id"] for x in windows if x["status"] in ("queued", "running")],
                "missing": [x["window"] for x in windows if x["status"] == "missing"],
                "no_data": [x["window"] for x in windows if x["status"] == "no_data"],
            }

        windows, queued = plan_okien(req.pair, hotove, vo_fronte, od, do, "", engine)
        out = {"strategy": strategy, "profile": req.profile, "pair": req.pair, "timeframe": req.timeframe,
               "engine": engine, "config_key": config_key, "market": f"{req.pair}|{req.timeframe}",
               **suhrn(windows, queued)}

        # Syntetické dvojča páru (premiešané bary): to isté zadanie na trhu bez štruktúry
        # patrí k analytike vždy - kladný edge tam je nález o backteste, nie o stratégii.
        # Dvojča sa vyrobí pri prvom Spočítať, potom je pevné ako každý recept.
        out["synthetic"] = _plan_twin(req, strategy, engine, okna, norm, plan_okien, suhrn)
        out["pending"] = out["pending"] + out["synthetic"].get("pending", [])
        return out

    def _plan_twin(req: AnalyticsPrepareRequest, strategy: str, engine: str, okna: list[str],
                   norm: dict[str, Any], plan_okien, suhrn) -> dict[str, Any]:
        from ... import synthetic as syn_mod

        if req.pair in syn_mod.synthetic_symbols():
            return {"pair": None, "note": "pár je sám syntetický"}
        dvojca = syn_mod.twin_for(req.pair)
        if dvojca is None and req.dry_run:
            return {"pair": None, "note": "syntetický trh páru vznikne pri Spočítať (premiešané bary páru)"}
        if dvojca is None:
            try:
                dvojca = syn_mod.ensure_twin(req.pair)
            except (FileNotFoundError, ValueError, KeyError) as exc:
                return {"pair": None, "note": f"syntetický trh sa nedá vyrobiť: {exc}"}
        key, inst = dvojca
        recept = syn_mod.recipes().get(key)
        od, do = (recept.timerange.split("-") + ["", ""])[:2] if recept else ("", "")
        moznosti = engines.available(inst, req.timeframe)
        engine_dvojcata = engine if engine in moznosti else (moznosti[0] if moznosti else engine)
        hotove: dict[str, dict[str, Any]] = {}
        for rec in store.all():
            s = rec.get("settings") or {}
            if (strategy_of(rec) != strategy or rec.get("status") != "done" or s.get("pair") != inst.symbol
                    or s.get("timeframe") != req.timeframe or s.get("timerange") not in okna
                    or (s.get("engine") or engine_dvojcata) != engine_dvojcata
                    or s.get("sweep") or s.get("plateau") or not _same_config(norm, rec)):
                continue
            w = s["timerange"]
            if w not in hotove or rec["id"] > hotove[w]["id"]:
                hotove[w] = rec
        vo_fronte: dict[str, dict[str, Any]] = {}
        for j in runner.snapshot():
            s = j.get("settings") or {}
            job = runner.job(j["id"])
            if (s.get("pair") == inst.symbol and s.get("timeframe") == req.timeframe
                    and s.get("timerange") in okna and (s.get("strategy") or "ibs") == strategy
                    and job is not None and _same_config(norm, {"settings": s, "params": job.params})):
                vo_fronte[s["timerange"]] = j
        windows, queued = plan_okien(inst.symbol, hotove, vo_fronte, od, do, " · syntetický trh", engine_dvojcata)
        return {"pair": inst.symbol, "key": key, "engine": engine_dvojcata, **suhrn(windows, queued)}

    return router
