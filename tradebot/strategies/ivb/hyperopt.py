"""Čo o ladení IVB vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["IvbHyperopt"]


class IvbHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Prepis cudzej stratégie len na porovnanie — defaulty sú z predlohy. Stop 3 ATR a cieľ 2 ATR "
                           "chcú WR nad 60 %; ladiť pomer IB, objem a stop / cieľ.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "maxContractionRatio": {"low": 0.5, "high": 1.5},
        "volSurgeMult": {"low": 0.8, "high": 3.0},
        "slAtrMult": {"low": 1.0, "high": 4.0},
        "tpAtrMult": {"low": 1.0, "high": 6.0},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {}

    WARN: ClassVar[dict[str, str]] = {}
