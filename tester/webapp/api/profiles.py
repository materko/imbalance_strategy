"""Profily stratégie: zoznam, uloženie, premenovanie, zmazanie (`/api/profiles`)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from tradebot.core.config import ConfigError
from tradebot.strategies import STRATEGIES

from .. import profiles as user_profiles
from ..runner import (
    REPO, default_params, instrument_for_pair, list_profiles, profile_info, profile_instruments,
    profile_titles,
)
from ..store import strategy_of
from .context import AppContext
from .models import ProfileSaveRequest, ProfileRenameRequest


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store

    @router.get("/api/profiles")
    def profiles_list(strategy: str = Query("ibs")):
        """Profily stratégie do formulára: z repozitára (nemenné) a vlastné (menné aj mazateľné)."""
        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        return {"strategy": strategy, "profiles": list_profiles(strategy), "user_profiles": user_profiles.user_names(strategy),
                "profile_titles": profile_titles(strategy), "profile_instruments": profile_instruments(strategy),
                "profile_info": profile_info(strategy)}

    @router.post("/api/profiles")
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

    @router.patch("/api/profiles/{name}")
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

    @router.delete("/api/profiles/{name}")
    def profile_delete(name: str, strategy: str = Query("ibs")):
        try:
            if not user_profiles.delete(name):
                raise HTTPException(404, f"profil {name} neexistuje")
        except user_profiles.ProfileError as exc:
            raise HTTPException(422, str(exc))
        return {"ok": True, **profiles_list(strategy)}

    @router.get("/api/profiles/{name:path}")
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
                "missing": user_profiles.missing_fields(target, strategy),
                "timeframe": setup.get("timeframe"), "settings": setup,
                "base": user_profiles.base_of(name, strategy),
                "kind": "user" if user_profiles.is_user(name, strategy) else "builtin"}

    return router
