"""Čo o ladení DAILY OPEN vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["DailyOpenHyperopt"]


class DailyOpenHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = "Autor tvrdí, že prah (10–40 b.), stop a čas výstupu sú stabilné; filtre volatility a smeru zvyšujú priemerný obchod."

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "entryMode": {"choices": ["stop", "close"]},
        "breakMode": {"choices": ["any", "before"]},
        "exitH": {"low": 11, "high": 16},
        "entryStartH": {"low": 4, "high": 10},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "hour": "entryStartH",
        "direction": "tradeDirection",
    }

    WARN: ClassVar[dict[str, str]] = {
        "breakPts": "body ceny sú viazané na NQ / MNQ / NAS100",
        "slPts": "body ceny sú viazané na NQ / MNQ / NAS100",
    }
