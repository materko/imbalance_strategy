"""Čo o ladení FVG POLARITY vieme — tri čísla tvaru obchodu, nič viac."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["FvgPolarityHyperopt"]


class FvgPolarityHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = (
        "Stratégia má tri rozhodnutia: veľkosť FVG, stop a kde v medzere je cieľ. Stop a cieľ menia "
        "pomer výhra/prehra najviac — laď ich ako prvé."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "slPoints": {"low": 5.0, "high": 60.0, "step": 5.0, "unit": "abs"},
        "tpLevel": {"choices": ["near", "mid", "far"]},
        "fvgMinSize": {"low": 0.0, "high": 30.0, "step": 2.5, "unit": "abs"},
        "tradeDirection": {"choices": ["Both", "Long only", "Short only"]},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "sl": ("slPoints", "vzdialenosť stopu v bodoch; veľkosť sa dopočíta na rovnaké riziko"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slPoints",
        "rr_planned": "tpLevel",
        "direction": "tradeDirection",
    }

    WARN: ClassVar[dict[str, str]] = {
        "fvgMaxSize": "strop, nie signál — ladením sa z neho stane skrytý filter dní",
    }
