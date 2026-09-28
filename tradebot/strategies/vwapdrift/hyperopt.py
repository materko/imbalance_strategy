"""Čo o ladení Drift VWAP vieme — odporúčania, varovania, väzby.

Video dáva len kostru (drift, prvý pullback); stop, cieľ a prahy sú odhady. Ladiť sa
preto majú najprv rozhodnutia o **tvare obchodu** — RR, rezerva stopu, kotva VWAP —
a až potom prahy driftu a odchodu, ak vôbec. Na IBS ladenie desiatich prahov naraz
našlo presne ladený rok (docs/merania/HYPEROPT_btcusdt_2026-09-04.md).
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["VwapDriftHyperopt"]


class VwapDriftHyperopt(StrategyHyperopt):
    """Ladenie pullbacku k VWAP: málo stupňov voľnosti, prahy v ATR."""

    NOTE: ClassVar[str] = (
        "Kotva VWAP (`vwapAnchor`) mení, čo stratégia vôbec meria — porovnaj ny_open a session "
        "ako dva behy. Lad najprv RR a rezervu stopu; prahy driftu a odchodu až potom."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        # Druh vstupu a stopu menia tvar obchodu najviac — porovnaj ich ako prvé.
        "entryMode": {"choices": ["close", "limit", "stop", "reaction", "pinbar", "engulfing"]},
        "slMode": {"choices": ["pullback", "candle", "vwap", "atr", "swing"]},
        "rrRatio": {"low": 0.75, "high": 4.0, "step": 0.25},
        "slBufferAtr": {"low": 0.0, "high": 1.0, "step": 0.1, "unit": "atr"},
        "driftMinAtr": {"low": 0.0, "high": 0.5, "step": 0.05, "unit": "atr"},
        "awayAtr": {"low": 0.0, "high": 3.0, "step": 0.25, "unit": "atr"},
        "tradeDirection": {"choices": ["Both", "Long only", "Short only"]},
    }

    #: Ktorý parameter robí staticky to, čo model mení za behu.
    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR); riziko na obchod sa nemení"),
        "sl": ("slBufferAtr", "ako ďaleko za pullback ide stop; veľkosť sa dopočíta tak, aby "
                              "riziko na obchod ostalo rovnaké"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slBufferAtr",
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "hour": "entryWindowMinutes",
        "exit_reason": "closeAtSessionEnd",
        "regime_trend": "driftMinAtr",
        "regime_align": "entryMode",
        "duration_min": "slMode",
    }

    WARN: ClassVar[dict[str, str]] = {
        "pbWickPct": "tvar pin baru — filter citlivosti, nie štruktúra obchodu",
        "pbBodyPct": "to isté ako pbWickPct",
        "touchTolAtr": "filter citlivosti, nie štruktúra obchodu — ladí sa ľahko a prefituje ešte ľahšie",
        "driftBars": "spolu s driftMinAtr určuje to isté; laď len jeden z nich",
        "sessionStartH": "otvorenie seansy nie je parameter, je to fakt o trhu",
        "maxTradesPerDay": "strop, nie signál — ladením sa z neho stane skrytý filter dní",
        "vwapAnchor": "mení, čo stratégia meria; porovnaj kotvy ako samostatné behy, nelaď to",
        "vwapPeriod": "to isté: 15m a graf sú dve verzie indikátora, nie prah",
    }
