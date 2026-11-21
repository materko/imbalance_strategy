"""Čo o ladení IB RETRACE 1.0 vieme."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["IbRetHyperopt"]


class IbRetHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Úrovne sú zlomky šírky IB; stop má sedieť za úrovňou max retracementu zo štatistiky "
                           "(IB Lab), nie byť vyladený na najlepší výsledok.")
    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "entryRetr": {"low": 0.0, "high": 0.5, "step": 0.05},
        "slRetr": {"low": 0.5, "high": 1.0, "step": 0.05},
        "tpExt": {"low": 0.25, "high": 1.0, "step": 0.05},
        "lastEntry": {"low": 1130, "high": 1500, "step": 30},
    }
    AI_ADJUSTABLE = {"size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
                     "tp": ("tpExt", "cieľ — extenzia IB")}
    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"direction": "tradeDirection"}
    WARN: ClassVar[dict[str, str]] = {"slRetr": "má vychádzať zo štatistiky návratu, nie z hyperoptu"}
