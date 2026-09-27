"""Čo o ladení Liquidity vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["LiquidityHyperopt"]


class LiquidityHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Spúšťač (`tradeMode`) a TF likvidity menia stratégiu najviac — lad ich ako "
                           "prvé, až potom vstupný model, stop a cieľ.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "tradeMode": {"choices": ["sweep", "breakout", "draw"]},
        "entryModel": {"choices": ["imbalance", "pinbar", "any", "close"]},
        "liqPivotLen": {"low": 2, "high": 10},
        "slMode": {"choices": ["level", "signal", "swing", "atr"]},
        "rrRatio": {"low": 0.5, "high": 3.0, "step": 0.25},
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
        "regime_align": "tradeMode",
    }

    WARN: ClassVar[dict[str, str]] = {
        "liqEqualTolAtr": "mení, čo sa zlúči do jednej úrovne — ladiť opatrne",
        "breakBufferAtr": "malý prah s veľkým vplyvom na počet obchodov",
        "cooldownBars": "technický parameter, nie edge",
        "maxTradesPerDay": "strop, nie signál",
    }
