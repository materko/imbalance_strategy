"""Čo o ladení SD Zones vieme — odporúčania, varovania, väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["SDZoneHyperopt"]


class SDZoneHyperopt(StrategyHyperopt):
    """Ladenie SD zón: málo stupňov voľnosti, prahy v ATR."""

    NOTE: ClassVar[str] = (
        "Dve rozhodnutia menia stratégiu viac než ladenie prahov: sila impulzu "
        "(`impulseMinBodyAtr`) a šírka zóny (`zoneMode`). Lad ich ako prvé a zvlášť."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "impulseMinBodyAtr": {"low": 0.4, "high": 2.0, "step": 0.2, "unit": "atr"},
        "zoneMode": {"choices": ["pfz", "wfz"]},
        "rrRatio": {"low": 1.5, "high": 5.0, "step": 0.5},
        "entryDepthPct": {"low": 0, "high": 100},
        "patterns": {"choices": ["all", "continuation", "reversal"]},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR); riziko na obchod sa nemení"),
        "sl": ("slBufferAtr", "ako ďaleko za hranu zóny ide stop"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slBufferAtr",
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "hour": "tradeStartH",
        "exit_reason": "maxHoldBars",
        "duration_min": "maxZoneAgeBars",
        "regime_align": "useTrendFilter",
        "regime_trend": "patterns",
    }

    WARN: ClassVar[dict[str, str]] = {
        "baseMaxBodyPct": "prah citlivosti, nie štruktúra obchodu — prefituje sa ľahko",
        "impulseMinBodyPct": "to isté; ladí sa spolu s impulseMinBodyAtr a jedno maskuje druhé",
        "maxZones": "technický strop, nie signál",
        "maxTradesPerDay": "strop, nie signál — ladením sa z neho stane skrytý filter dní",
        "requireFresh": "vypnutie zmení myšlienku stratégie, nie jej nastavenie; meraj to zvlášť",
    }
