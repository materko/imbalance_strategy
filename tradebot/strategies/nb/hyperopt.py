"""Čo o ladení NB vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["NbHyperopt"]


class NbHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Konsolidácia (počet sviečok a šírka v ATR) rozhoduje, koľko je obchodov; trend H4 a SMA grafu, "
                           "čo sa smie. RR 3 a miesto do cieľa 2,5 R sú z videa — meniť opatrne, nie podľa jedného roka.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "consBars": {"low": 4, "high": 24},
        "rrRatio": {"low": 1.5, "high": 4.0},
        "roomMinR": {"low": 0.0, "high": 3.0},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
        "rr": ("rrRatio", "pomer cieľa k riziku"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "hour": "entryEndH",
    }

    WARN: ClassVar[dict[str, str]] = {}
