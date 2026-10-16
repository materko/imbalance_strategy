"""Čo o ladení NOA 1.0 vieme."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["NoaHyperopt"]


class NoaHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Intraday momentum podľa Concretum (Zarattini, Aziz, Barbon 2024). Zdroj: 14 dní, pásmo × 1, "
                           "kontroly každých 30 min, výstup cez VWAP a o 16:00 — ladiť šírku pásma a dĺžku priemeru, "
                           "nie poistku.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "lookbackDays": {"low": 7, "high": 30, "step": 1},
        "volMult": {"low": 0.8, "high": 2.0, "step": 0.05},
        "checkEvery": {"choices": [15, 30, 60]},
        "lastEntryMin": {"low": 180, "high": 360, "step": 30},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"sl_pct": "hardStopPct", "direction": "tradeDirection"}

    WARN: ClassVar[dict[str, str]] = {"maxTradesPerDay": "strop, nie signál", "hardStopPct": "poistka, nie signál"}
