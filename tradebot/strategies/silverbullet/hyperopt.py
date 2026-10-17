"""Čo o ladení Silver Bullet 1.0 vieme."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["SilverBulletHyperopt"]


class SilverBulletHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("ICT Silver Bullet: okno 10–11 NY, sweep likvidity, FVG, limitka. Najviac 1 obchod denne — "
                           "pozor na hranicu 150 obchodov za rok. Najprv zdroj likvidity a FVG, potom cieľ; najviac "
                           "4 parametre naraz (smernica testovania).")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "liqPivotLen": {"low": 2, "high": 6},
        "fvgMinAtr": {"low": 0.0, "high": 0.6, "step": 0.1},
        "fvgMaxBars": {"low": 3, "high": 20, "step": 1},
        "minRR": {"low": 0.5, "high": 3.0, "step": 0.25},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR)"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"rr_planned": "rrRatio", "direction": "tradeDirection"}

    WARN: ClassVar[dict[str, str]] = {"maxTradesPerDay": "strop, nie signál"}
