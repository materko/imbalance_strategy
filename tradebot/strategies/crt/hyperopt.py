"""Čo o ladení CRT + TBS vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["CrtHyperopt"]


class CrtHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("TF rangu, druh výberu (telo / knôt) a vstupný model menia stratégiu najviac — lad ich "
                           "ako prvé, až potom stop a cieľ.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "rangeTF": {"choices": [60, 240]},
        "sweepKind": {"choices": ["body", "wick", "any"]},
        "entryModel": {"choices": ["model1", "cisd", "mss_fvg"]},
        "tpMode": {"choices": ["mid", "opposite", "rr"]},
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
        "regime_align": "sweepKind",
    }

    WARN: ClassVar[dict[str, str]] = {
        "maxTradesPerDay": "strop, nie signál",
        "validBars": "dlhšia platnosť setupu = viac obchodov ďaleko od výberu",
    }
