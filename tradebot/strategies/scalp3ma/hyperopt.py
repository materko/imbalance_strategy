"""Čo o ladení Scalping 3MA + RSI + fraktál vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["Scalp3MaHyperopt"]


class Scalp3MaHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Stop (druh a veľkosť) a RR menia výsledok najviac; dĺžky priemerov a strana fraktálu "
                           "menia počet obchodov.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "slMode": {"choices": ["points", "atr", "fractal"]},
        "fractalSide": {"choices": ["pullback", "trend", "any"]},
        "rrRatio": {"low": 1.0, "high": 3.0, "step": 0.25},
        "maxTradesPerDay": {"low": 1, "high": 5},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR)"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slAtr",
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "hour": "tradeStartH",
        "exit_reason": "rsiExit",
        "regime_align": "requireMaOrder",
    }

    WARN: ClassVar[dict[str, str]] = {
        "maxTradesPerDay": "strop, nie signál — video varuje pred preobchodovaním",
        "slPoints": "body ceny sú viazané na trh (5 pipov na EURUSD = 0,0005)",
    }
