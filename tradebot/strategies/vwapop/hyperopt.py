"""Čo o ladení VWAP OP vieme — odporúčania, varovania, väzby.

Skript dáva len kostru (drift na HTF, prvý pullback, pevný stop za VWAP); RR a SL sú
odhady na test, nie výsledok videa. Ladiť sa preto majú najprv tvar obchodu (RR, SL)
a až potom prahy driftu/tolerancie, ak vôbec.
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["VwapOpHyperopt"]


class VwapOpHyperopt(StrategyHyperopt):
    """Ladenie pullbacku k VWAP na HTF: málo stupňov voľnosti, prahy v ATR."""

    NOTE: ClassVar[str] = (
        "Drift sa meria ATR HTF (`htf`), tolerancia a stop ATR grafu — nemiešaj ich pri ladení. "
        "`rthSess`/`tradeWin`/`flatTime` sú fakty o seanse, nie parametre na ladenie."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "rr": {"low": 0.75, "high": 4.0, "step": 0.25},
        "slAtr": {"low": 0.1, "high": 2.0, "step": 0.1, "unit": "atr"},
        "driftAtr": {"low": 0.0, "high": 0.5, "step": 0.05, "unit": "atr"},
        "tolAtr": {"low": 0.0, "high": 0.5, "step": 0.05, "unit": "atr"},
        "useBE": {"choices": [False, True]},
    }

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rr", "vzdialenosť take profitu (R); riziko na obchod sa nemení"),
        "sl": ("slAtr", "ako ďaleko od VWAP ide stop; veľkosť sa dopočíta tak, aby riziko ostalo rovnaké"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slAtr",
        "rr_planned": "rr",
        "direction": "allowLong",
        "hour": "tradeWin",
        "exit_reason": "closeEOD",
        "regime_trend": "driftAtr",
    }

    WARN: ClassVar[dict[str, str]] = {
        "maxTrades": "strop, nie signál — ladením sa z neho stane skrytý filter dní",
        "driftLen": "spolu s driftAtr určuje to isté; laď len jeden z nich",
        "rthSess": "otvorenie seansy nie je parameter, je to fakt o trhu",
        "htf": "mení, čo drift vôbec meria — porovnaj hodnoty ako samostatné behy, nelaď to",
    }
