"""Čo o ladení M2 vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["M2Hyperopt"]


class M2Hyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Pravidlá sú z podkladu presne dané (50 % rozsahu, potvrdenie celým telom, limit na hrane M2, stop za M2). "
                           "Ladiť sa dá RR, rezerva stopu, platnosť limitky a filter EMA — nie definícia M2.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "rrRatio": {"low": 1.0, "high": 3.0},
        "slTicks": {"low": 0, "high": 8},
        "limitMaxBars": {"low": 0, "high": 60},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
        "rr": ("rrRatio", "pomer cieľa k riziku"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {}

    WARN: ClassVar[dict[str, str]] = {}
