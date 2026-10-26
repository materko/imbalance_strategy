"""Čo o ladení SD ZÓNY EURUSD vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["SdEurHyperopt"]


class SdEurHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Kvalita zóny: TF zóny, rýchlosť a veľkosť odchodu, výška zóny a čas vzniku; vstup len v Londýne. "
                           "RR a rezerva stopu menia výsledok menej než výber zón.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "zoneTF": {"low": 15, "high": 120},
        "depMaxBars": {"low": 2, "high": 12},
        "rrRatio": {"low": 1.0, "high": 3.0},
        "entryDepthPct": {"low": 0, "high": 50},
        "extremeBars": {"low": 0, "high": 24},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
        "rr": ("rrRatio", "pomer cieľa k riziku"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "hour": "entryEndH",
    }

    WARN: ClassVar[dict[str, str]] = {}
