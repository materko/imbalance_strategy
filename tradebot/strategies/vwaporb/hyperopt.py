"""Čo o ladení VWAP ORB vieme — ORB priestor a k nemu prerazenie VWAP; platí aj pre VwapOrbNet."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import Suggestion
from ..orb.hyperopt import OrbHyperopt

__all__ = ["VwapOrbHyperopt"]


class VwapOrbHyperopt(OrbHyperopt):
    NOTE: ClassVar[str] = ("VWAP ORB = ORB, kde rozhoduje aj VWAP za hranicou rangu; ladí sa range, RR a o koľko "
                           "musí byť VWAP za hranicou. Kotva a perióda VWAP sú voľba trhu, nie páka na ladenie.")
    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "nyRangeMinutes": {"low": 5, "high": 60, "step": 5},
        "rrRatio": {"low": 0.75, "high": 4.0, "step": 0.25},
        "slRangePct": {"low": 25, "high": 100, "step": 5},
        "vwapBreakAtr": {"low": 0.0, "high": 1.0, "step": 0.05},
    }
    WARN: ClassVar[dict[str, str]] = {**OrbHyperopt.WARN,
                                      "vwapPeriod": "perióda VWAP mení definíciu signálu, nie jeho citlivosť"}
