"""Čo o ladení JSS vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["JssHyperopt"]


class JssHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("TF štruktúry, swingLen a spúšťač (BOS / CHoCH) menia stratégiu najviac — lad ich "
                           "ako prvé, až potom zónu, vstupný model, stop a cieľ.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "structTF": {"choices": [5, 10, 15, 30]},
        "swingLen": {"low": 2, "high": 8},
        "triggerMode": {"choices": ["bos", "choch", "both"]},
        "entryModel": {"choices": ["touch", "imbalance", "pinbar", "any"]},
        "rrRatio": {"low": 1.0, "high": 3.0, "step": 0.25},
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
        "exit_reason": "maxHoldBars",
        "regime_align": "triggerMode",
    }

    WARN: ClassVar[dict[str, str]] = {
        "impulseAtr": "mení, ktorá sviečka je začiatok impulzu, a tým aj zónu",
        "cooldownBars": "technický parameter, nie edge",
        "maxTradesPerDay": "strop, nie signál",
    }
