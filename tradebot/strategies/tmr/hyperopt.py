"""Čo o ladení T-MEAN REVERSION 1.0 vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["TmrHyperopt"]


class TmrHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = "Prepis cudzej stratégie (roboquant) — defaulty sú z predlohy; ladí sa podľa smernice."

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {}

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {}

    WARN: ClassVar[dict[str, str]] = {}
