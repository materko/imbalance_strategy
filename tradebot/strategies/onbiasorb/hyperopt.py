"""Čo o ladení Overnight Bias ORB vieme."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["OnBiasOrbHyperopt"]


class OnBiasOrbHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Laď najprv SL (% ATR) a RR; začiatok overnight rangu (0 alebo 2300) porovnaj ako "
                           "dva behy. Časy openu a exitu sú fakty o seanse.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "slPct": {"low": 10.0, "high": 60.0, "step": 5.0},
        "rr": {"low": 1.0, "high": 4.0, "step": 0.5},
        "adxMin": {"low": 10.0, "high": 35.0, "step": 2.5},
        "onStartHHMM": {"choices": [0, 2300]},
    }

    AI_ADJUSTABLE = {"size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia")}

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slPct", "rr_planned": "rr", "hour": "minEntryHHMM", "exit_reason": "exitHHMM",
        "regime_trend": "adxMin",
    }

    WARN: ClassVar[dict[str, str]] = {
        "rthHHMM": "otvorenie trhu nie je parameter, je to fakt o trhu",
        "adxLen": "spolu s adxMin určuje to isté; laď len jeden z nich",
    }
