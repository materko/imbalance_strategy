"""Čo o ladení ASIA SWEEP 1.0 vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["AsiaSweepHyperopt"]


class AsiaSweepHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = "Výsledok určuje hlavne vstupný model, RR a okno sweepu; filter naked POC znižuje počet obchodov."

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "entryModel": {"choices": ["imbalance", "pinbar", "any", "close"]},
        "rrRatio": {"low": 1.0, "high": 4.0, "step": 0.25},
        "tpMode": {"choices": ["rr", "range", "mid", "npoc"]},
        "slMode": {"choices": ["sweep", "signal", "atr"]},
        "entryBars": {"low": 3, "high": 36},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR)"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "hour": "sweepStartH",
    }

    WARN: ClassVar[dict[str, str]] = {
        "maxTradesPerDay": "strop, nie signál",
    }
