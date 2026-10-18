"""Čo o ladení TKS 1.0 vieme."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["TksHyperopt"]


class TksHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = "NQ Kompas = trend dňa; hranice a RR menia počet a kvalitu signálov, konštanty Kompasu sa neladia."
    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "loLevel": {"low": 10, "high": 40, "step": 5},
        "hiLevel": {"low": 60, "high": 90, "step": 5},
        "nConf": {"low": 1, "high": 6, "step": 1},
        "rrRatio": {"low": 0.5, "high": 2.0, "step": 0.25},
        "pivLen": {"low": 2, "high": 8, "step": 1},
    }
    AI_ADJUSTABLE = {"size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
                     "tp": ("rrRatio", "vzdialenosť take profitu (RR)")}
    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"rr_planned": "rrRatio", "direction": "tradeDirection"}
    WARN: ClassVar[dict[str, str]] = {"maxTradesPerSession": "strop, nie signál"}
