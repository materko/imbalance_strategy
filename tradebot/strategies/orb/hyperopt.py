"""Čo o ladení Opening Range Breakout vieme — platí aj pre ORBNet (C# jadro, tie isté parametre)."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["OrbHyperopt"]


class OrbHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = ("ORB stojí na dĺžke rangu a na tom, kam padne SL a TP; časy seáns sa neladia "
                           "(sú to burzové hodiny, nie parameter), filtre objemu a EMA až keď drží jadro.")
    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        # dĺžka opening rangu: najsilnejšia páka - mení počet aj šírku rangu, teda SL
        "nyRangeMinutes": {"low": 5, "high": 60, "step": 5},
        # TP ako násobok rizika
        "rrRatio": {"low": 0.75, "high": 4.0, "step": 0.25},
        # SL ako podiel rangu (slMode=Opposite: 100 % = druhá strana rangu)
        "slRangePct": {"low": 25, "high": 100, "step": 5},
        # o koľko musí close prekonať hranicu rangu (v ATR)
        "breakBufferAtr": {"low": 0.0, "high": 0.5, "step": 0.05},
        # ako dlho po rangu sa ešte smie vstúpiť
        "entryWindowMinutes": {"low": 30, "high": 240, "step": 30},
    }
    WARN: ClassVar[dict[str, str]] = {
        "nyStartH": "čas otvorenia burzy, nie parameter — ladením sa nájde náhodná hodina",
        "nyStartM": "čas otvorenia burzy, nie parameter",
        "maxTradesPerDay": "strop, nie signál",
    }
    AI_ADJUSTABLE = {"size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
                     "tp": ("rrRatio", "vzdialenosť take profitu (RR)")}
    FEATURE_PARAMS: ClassVar[dict[str, str]] = {"rr_planned": "rrRatio", "direction": "tradeDirection"}
