"""Čo o ladení VWAP ADX vieme — odporúčania a varovania."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["VwapAdxHyperopt"]


class VwapAdxHyperopt(StrategyHyperopt):
    """Málo stupňov voľnosti; TP a SL sú v baroch 1m grafu."""

    NOTE: ClassVar[str] = (
        "Časy rangu a exitu sú fakty o seanse, nie prahy. Lad najprv TP/SL (počty barov) a prah ADX; "
        "ukotvenie VWAP porovnaj ako dva samostatné behy."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "tpBars": {"low": 3, "high": 30, "step": 1},
        "slBars": {"low": 5, "high": 60, "step": 5},
        "adxMin": {"low": 10.0, "high": 35.0, "step": 2.5},
        "vwapAnchor": {"choices": ["RTH 8:30 CT", "Polnoc CT"]},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slBars",
        "rr_planned": "tpBars",
        "hour": "orEndHHMM",
        "exit_reason": "exitHHMM",
        "regime_trend": "adxMin",
    }

    WARN: ClassVar[dict[str, str]] = {
        "orStartHHMM": "otvorenie seansy nie je parameter, je to fakt o trhu",
        "maxTrades": "strop, nie signál — ladením sa z neho stane skrytý filter dní",
        "adxLen": "spolu s adxMin určuje to isté; laď len jeden z nich",
    }
