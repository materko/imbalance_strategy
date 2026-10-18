"""Čo o ladení NOC + PONDELOK vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["NocPonHyperopt"]


class NocPonHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Štrukturálny jav (nočný drift, pondelok). Meranie MNQ 2019–2026: výsledok je stabilný v čase vstupu "
                           "15:30–15:55, výstupe 23:00–9:30 a SMA 50–200; ladenie nemá hľadať úzky vrchol.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "nightExitH": {"low": 0, "high": 9},
        "smaLen": {"low": 50, "high": 200},
        "useMonday": {"choices": [True, False]},
        "stopPct": {"low": 0.0, "high": 3.0},
    }

    AI_ADJUSTABLE = {
        "size": ("qty", "počet kontraktov"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "hour": "nightExitH",
        "weekday": "useMonday",
    }

    WARN: ClassVar[dict[str, str]] = {
        "skipRoll": "bez vynechania rollu sú výsledky na spojitých dátach skreslené skokom medzi kontraktmi",
    }
