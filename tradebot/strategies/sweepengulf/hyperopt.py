"""Čo o ladení SWEEPING ENGULF 1.0 vieme (z videa LuxAlgo)."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["SweepEngulfHyperopt"]


class SweepEngulfHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Video: najlepšie 4h, predošlá sviečka smerom manipulácie, EMA 200; stop ATR 5 + RR 1,5 dal PF ~2 "
                           "na málo obchodoch (prefitované). Najviac 4 parametre naraz (smernica testovania).")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "prevCandle": {"choices": ["opposite", "same", "any"]},
        "slMethod": {"choices": ["candle", "atr"]},
        "atrMult": {"low": 1.0, "high": 5.0, "step": 0.5},
        "rrRatio": {"low": 1.0, "high": 3.0, "step": 0.5},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR)"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"rr_planned": "rrRatio", "direction": "tradeDirection"}

    WARN: ClassVar[dict[str, str]] = {}
