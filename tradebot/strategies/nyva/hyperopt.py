"""Čo o ladení NY VA BREAKOUT vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["NyVaHyperopt"]


class NyVaHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Prieraz z value area prvej hodiny NY. Ladí sa koniec rangeu, RR a koniec vstupov; "
                           "počet riadkov profilu a value area % menia úrovne len jemne.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "rangeEndH": {"low": 10, "high": 11},
        "rrRatio": {"low": 0.5, "high": 2.0},
        "entryEndH": {"low": 11, "high": 16},
        "slBufferTicks": {"low": 0, "high": 40},
        "valueAreaPct": {"low": 60, "high": 80},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
        "rr": ("rrRatio", "pomer cieľa k riziku"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "hour": "entryEndH",
    }

    WARN: ClassVar[dict[str, str]] = {}
