"""Čo o ladení VALUE AREA REVERSION 1.0 vieme (z videa LuxAlgo / Fabio Valentini)."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["VaRevHyperopt"]


class VaRevHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Video: najsilnejšie 15m a 30m, profil predošlého dňa, návrat do 5 barov, voliteľne pohltenie. "
                           "Indikátor nebol backtestovaný — čísla treba zmerať. Najviac 4 parametre naraz.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "profileSource": {"choices": ["previous", "current"]},
        "maxBarsOutside": {"low": 2, "high": 10},
        "reclaimVolMult": {"low": 0.0, "high": 2.0, "step": 0.25},
        "tpMode": {"choices": ["va", "poc", "rr"]},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"direction": "tradeDirection"}

    WARN: ClassVar[dict[str, str]] = {"maxTradesPerDay": "strop, nie signál"}
