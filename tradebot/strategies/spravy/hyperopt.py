"""Čo o ladení SPRÁVY vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["SpravyHyperopt"]


class SpravyHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Obchodov je málo (~50 za rok) — ladiť len pár čísel (noha, držanie, rezerva stopu) a overovať po rokoch; "
                           "výber typov správ je z prieskumu, nie z hyperoptu.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "trendHold": {"low": 60, "high": 480},
        "fadeHold": {"low": 30, "high": 240},
        "trendTo": {"low": 30, "high": 90},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {}

    WARN: ClassVar[dict[str, str]] = {}
