"""Čo o ladení MTK ZONE vieme (Pine predloha na TradingView, 10. 11. 2026)."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["MtkZoneHyperopt"]


class MtkZoneHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Počet zón riadi hlavne minConf a maxZones (minConf 1 = priveľa obchodov, PF < 1). "
                           "Najviac 4 parametre naraz (smernica testovania).")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "minConf": {"low": 1, "high": 3, "step": 1},
        "volSpike": {"low": 1.5, "high": 3.0, "step": 0.5},
        "zoneTf1": {"choices": [5, 15]},
        "rrRatio": {"low": 0.5, "high": 2.0, "step": 0.25},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR)"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"rr_planned": "rrRatio", "direction": "tradeDirection"}

    WARN: ClassVar[dict[str, str]] = {}
