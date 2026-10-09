"""Čo o ladení Volt Break vieme."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["VoltBreakHyperopt"]


class VoltBreakHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = "Laď najprv noise (%) a TP/SL; časy okna sú z videa a sú faktom o seanse."

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "noisePct": {"low": 10.0, "high": 60.0, "step": 5.0},
        "tpUsd": {"low": 400.0, "high": 2000.0, "step": 100.0},
        "slUsd": {"low": 500.0, "high": 2500.0, "step": 250.0},
        "atrSource": {"choices": ["Seansa 0:00–16:00 CT (ako vo videu)", "Denné sviečky burzy"]},
    }

    AI_ADJUSTABLE = {"size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia")}

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slUsd", "rr_planned": "tpUsd", "hour": "startHHMM", "exit_reason": "endHHMM",
    }

    WARN: ClassVar[dict[str, str]] = {
        "maxTrades": "strop, nie signál — ladením sa z neho stane skrytý filter dní",
        "avgLen": "spolu s atrLen určuje to isté; laď len jeden z nich",
    }
