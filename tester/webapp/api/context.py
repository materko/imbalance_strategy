"""Kontext aplikácie, ktorý dostane každý router pri zostavení."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from tradebot.core.env import getenv
from tradebot.strategies import STRATEGIES

from .. import profiles as user_profiles
from ..anstore import AnalyticsStore
from ..param_meta import param_metadata
from ..replay import ChartReplayer
from ..runner import (
    BacktestRunner, list_profiles, profile_info, profile_instruments, profile_titles,
)
from ..store import RunStore, strategy_of


class AppContext:
    """Stav zdieľaný routermi: sklady, fronta, prepočet grafov a defaulty stratégií."""

    def __init__(self, app: FastAPI, store: RunStore, runner: BacktestRunner,
                 replayer: ChartReplayer, anstore: AnalyticsStore) -> None:
        self.app = app
        self.store = store
        self.runner = runner
        self.replayer = replayer
        self.anstore = anstore
        #: Pine defaulty každej stratégie — proti nim sa počítajú odchýlky behu.
        self.defaults = {key: spec.config_cls().to_dict() for key, spec in STRATEGIES.items()}
        #: Metadáta formulára stratégie. Parametre a defaulty sú kód (nemenia sa za behu),
        #: zoznam profilov sa číta vždy nanovo — tester si ich cez API ukladá, premenúva a maže.
        self.param_meta = {key: param_metadata(spec) for key, spec in STRATEGIES.items()}
    #: Mriežka nemá strop: sweep má zmysel púšťať cez noc alebo na serveri a číslo,
    #: ktoré by sme vymysleli, by len prekážalo. Namiesto obmedzenia dostane tester
    #: odhad času vopred a tlačidlo, ktorým celú mriežku zruší naraz.
    #: `TRADEBOT_MAX_SWEEP_RUNS` strop zapne tomu, kto ho chce (0 = bez stropu).
        self.max_sweep_runs = max(0, int(getenv("MAX_SWEEP_RUNS", "0") or 0))

    def strategy_meta(self, key: str) -> dict[str, Any]:
        return {
            "params": self.param_meta[key],
            "defaults": self.defaults[key],
            "profiles": list_profiles(key),
            "profile_titles": profile_titles(key),
            "profile_instruments": profile_instruments(key),
            "profile_info": profile_info(key),
            "user_profiles": user_profiles.user_names(key),
        }

    def defaults_of(self, rec: dict[str, Any]) -> dict[str, Any]:
        return self.defaults.get(strategy_of(rec), self.defaults["ibs"])

    def chart_state(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Stav grafu behu: hotový (lokálne), počíta sa, zlyhal, chýba — alebo sa nedá."""
        if rec.get("status") != "done" or ((rec.get("settings") or {}).get("hyperopt") or {}).get("knobs"):
            return {"state": "unavailable"}
        return self.replayer.status(rec["id"])
