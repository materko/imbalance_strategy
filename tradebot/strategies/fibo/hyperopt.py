"""Čo o ladení Fibo vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["FiboHyperopt"]


class FiboHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("TF swingov, dĺžka swingu a minimálna noha určujú, čo je impulz — lad ich ako prvé; "
                           "potom úrovne, vstupný model, stop a cieľ.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "swingTF": {"choices": [5, 15, 30, 60]},
        "swingLen": {"low": 2, "high": 8},
        "entryModel": {"choices": ["imbalance", "pinbar", "any"]},
        "slMode": {"choices": ["leg", "pullback"]},
        "tpExtensionPct": {"choices": [0, 27, 61.8]},
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
        "regime_align": "requireBreak",
    }

    WARN: ClassVar[dict[str, str]] = {
        "maxTradesPerDay": "strop, nie signál",
        "levelTolAtr": "tolerancia mení, čo je ešte „pri úrovni\"",
    }
