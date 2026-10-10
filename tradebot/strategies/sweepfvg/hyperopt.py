"""Čo o ladení SWEEP FVG 1.0 vieme."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["SweepFvgHyperopt"]


class SweepFvgHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Výber likvidity → CHoCH / BOS → limitka na okraji FVG. Najprv TF likvidity a swing grafu, "
                           "potom FVG a cieľ; najviac 4 parametre naraz (smernica testovania).")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "structPivotLen": {"low": 2, "high": 6},
        "fvgMinAtr": {"low": 0.1, "high": 1.0, "step": 0.1},
        "entryMaxBars": {"low": 5, "high": 40, "step": 5},
        "rrRatio": {"low": 1.0, "high": 4.0, "step": 0.5},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR)"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"rr_planned": "rrRatio", "direction": "tradeDirection"}

    WARN: ClassVar[dict[str, str]] = {"maxTradesPerDay": "strop, nie signál"}
