"""Čo o ladení INTRADAY 1.0 vieme."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["IntradayHyperopt"]


class IntradayHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Smernica obchodovania Martina: bias → likvidita → zóny 1H/15m/5m → limitka. Najviac 4 parametre "
                           "naraz (smernica testovania); definíciu zóny nemeniť spolu s cieľom.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "entryTF": {"choices": [5, 15, 60]},
        "legOutMinAtr": {"low": 1.0, "high": 3.0, "step": 0.5},
        "rrRatio": {"low": 1.0, "high": 3.0, "step": 0.5},
        "liqMode": {"choices": ["zone", "sweep", "off"]},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR)"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"rr_planned": "rrRatio", "direction": "tradeDirection"}

    WARN: ClassVar[dict[str, str]] = {"maxTradesPerDay": "strop, nie signál"}
