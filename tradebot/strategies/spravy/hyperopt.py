"""Čo o ladení SPRÁVY vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["SpravyHyperopt"]


class SpravyHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Obchodov je málo (~60 za rok, na jednu správu 8–12) — ladiť len pár čísel jedného pravidla (noha, vstup, držanie) "
                           "a overovať po rokoch; výber správ a režimov je z výskumu, nie z hyperoptu.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "r1Hold": {"low": 15, "high": 175},
        "r2Hold": {"low": 60, "high": 145},
        "r3Enter": {"low": 30, "high": 90},
        "r4Hold": {"low": 60, "high": 240},
        "r5Hold": {"low": 60, "high": 480},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {}

    WARN: ClassVar[dict[str, str]] = {}
