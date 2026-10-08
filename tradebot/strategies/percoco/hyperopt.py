"""Čo o ladení Craig Percoco 1.0 vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["PercocoHyperopt"]


class PercocoHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = "Cieľ v R a filtre 15m (smer, dotyk FVG) menia stratégiu najviac — laď ich ako prvé."

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "rrRatio": {"low": 1.0, "high": 4.0, "step": 0.5},
        "entryPct": {"low": 0, "high": 100, "step": 25},
        "useHtfPoi": {"choices": [True, False]},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR)"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slBufferAtr",
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "hour": "tradeStartH",
        "regime_align": "useHtfBias",
    }

    WARN: ClassVar[dict[str, str]] = {"maxTradesPerDay": "strop, nie signál"}
