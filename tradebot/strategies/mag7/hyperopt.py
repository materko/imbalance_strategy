"""Čo o ladení Mag7 + SPX sila vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["Mag7Hyperopt"]


class Mag7Hyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Prah sily a čas merania určujú, koľko dní sa obchoduje; potvrdenia VWAP / EMA / MAG7 "
                           "a stop za open NY menia kvalitu vstupu.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "thr": {"low": 3.0, "high": 8.0, "step": 0.5},
        "waitMin": {"low": 5, "high": 30},
        "entryEnd": {"low": 15, "high": 90},
        "emaLen": {"low": 20, "high": 200},
        "magLen": {"low": 2, "high": 20},
        "rr": {"low": 1.0, "high": 3.0, "step": 0.25},
        "slMode": {"choices": ["points", "open"]},
        "stockW": {"low": 0.0, "high": 2.0, "step": 0.5},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
        "tp": ("rr", "cieľ ako násobok stopu"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "rr_planned": "rr",
        "direction": "allowL",
        "hour": "waitMin",
    }

    WARN: ClassVar[dict[str, str]] = {
        "slPts": "body ceny sú viazané na NQ / MNQ",
        "minMove": "body ceny sú viazané na NQ / MNQ",
    }
