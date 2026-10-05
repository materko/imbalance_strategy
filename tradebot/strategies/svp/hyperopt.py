"""Čo o ladení Volume Profile POC vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["SvpHyperopt"]


class SvpHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Zdroj POC (predošlá seansa / vyvíjajúci sa), režim (odmietnutie / retest) a vstupný model "
                           "menia stratégiu najviac — lad ich ako prvé.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "pocSource": {"choices": ["previous", "developing"]},
        "tradeMode": {"choices": ["rejection", "retest", "both"]},
        "entryModel": {"choices": ["touch", "imbalance", "pinbar", "any"]},
        "rrRatio": {"low": 1.0, "high": 3.0, "step": 0.25},
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
        "exit_reason": "closeAtWindowEnd",
        "regime_align": "tradeMode",
    }

    WARN: ClassVar[dict[str, str]] = {
        "rowTicks": "výška riadku mení, kde POC vyjde — viazaná na tick trhu",
        "maxTradesPerDay": "strop, nie signál",
    }
