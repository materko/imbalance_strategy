"""Čo o ladení FPC 1.0 vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["FpcHyperopt"]


class FpcHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("Výsledok určuje hlavne cieľ (TP v bodoch alebo na férovej cene) a filtre proti trendovému "
                           "dňu; stop je podľa videa „náhodný\" a mení najmä veľkosť pozície.")

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "tpMode": {"choices": ["fixed", "fair"]},
        "maxLossRow": {"low": 1, "high": 4},
        "minPct": {"low": 60.0, "high": 120.0, "step": 10.0},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("revTP", "cieľ návratu v bodoch"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "revSL",
        "rr_planned": "revTP",
        "direction": "tradeDirection",
        "hour": "s1H",
    }

    WARN: ClassVar[dict[str, str]] = {
        "revTP": "body ceny sú viazané na NQ / MNQ / NAS100 — na inom trhu treba prepočítať",
        "maxTrades": "strop, nie signál",
    }
