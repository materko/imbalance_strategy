"""Čo o ladení Trendline Breakoutu vieme — odporúčania, varovania, väzby.

Priestor je zámerne úzky: len parametre, ktoré menia štruktúru obchodu (TF čiar, typ vstupu,
stop a RR) alebo definíciu trendovky (pivot, dotyky), nie citlivosť filtrov.
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["TrendlineHyperopt"]


class TrendlineHyperopt(StrategyHyperopt):
    """Ladenie trendline breakoutu."""

    NOTE: ClassVar[str] = (
        "TF trendoviek (`lineTF`) a typ vstupu (`entryMode`) menia stratégiu najviac — "
        "lad ich ako prvé a zvlášť, až potom stop a RR."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "lineTF": {"choices": ["15", "30", "60", "120", "240"]},
        "pivotLen": {"low": 2, "high": 10},
        "minTouches": {"low": 2, "high": 4},
        "entryMode": {"choices": ["close", "second_close", "retest", "retest_close"]},
        "slMode": {"choices": ["line", "break_candle", "swing", "atr"]},
        "rrRatio": {"low": 0.5, "high": 3.0, "step": 0.25},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR); riziko na obchod sa nemení"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slBufferAtr",
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "hour": "tradeStartH",
        "exit_reason": "maxHoldBars",
        "regime_align": "entryMode",
        "regime_trend": "lineSlope",
    }

    WARN: ClassVar[dict[str, str]] = {
        "minClosePosPct": "filter citlivosti, nie štruktúra obchodu — ladí sa ľahko a prefituje ešte ľahšie",
        "breakBufferAtr": "malý prah s veľkým vplyvom na počet obchodov",
        "touchTolAtr": "mení, čo je dotyk aj čo je platná čiara naraz — ladiť opatrne",
        "cooldownBars": "technický parameter, nie edge",
        "maxTradesPerDay": "strop, nie signál",
    }
