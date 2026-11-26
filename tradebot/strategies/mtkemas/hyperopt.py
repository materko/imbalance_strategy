"""Čo o ladení MTK EMAS vieme (štúdia Mac mini 25. 11. 2026)."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["MtkEmasHyperopt"]


class MtkEmasHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Štúdia: TF 1h–4h, len longy, filter EMA 200; vyberať podľa plató (susedné dĺžky), "
                           "výstup je dôležitejší než vstup.")
    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "slowLen": {"low": 80, "high": 200, "step": 10},
        "slAtr": {"low": 1.0, "high": 3.0, "step": 0.5},
        "trailAtr": {"low": 2.0, "high": 6.0, "step": 0.5},
    }
    AI_ADJUSTABLE = {"size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia")}
    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"direction": "tradeDirection"}
    WARN: ClassVar[dict[str, str]] = {"tradeDirection": "shorty v štúdii prehrávali"}
