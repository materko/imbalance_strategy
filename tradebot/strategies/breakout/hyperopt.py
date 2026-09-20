"""Čo o ladení Breakoutu vieme — odporúčania, varovania, väzby.

Priestor je zámerne úzky. Na IBS dopadlo ladenie desiatich prahov naraz tak, že víťazná
epocha bola na ladenom roku +34,8 % a všetky štyri out-of-sample roky stratové
(docs/merania/HYPEROPT_btcusdt_2026-09-04.md). Stratégia má pritom len dve úrovne, takže
je tu ešte menej čoho sa chytiť: ladiť treba rozhodnutia o **tvare obchodu**
(typ príkazu, RR, okno), nie citlivosť filtrov.
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["BreakoutHyperopt"]


class BreakoutHyperopt(StrategyHyperopt):
    """Ladenie prerazenia otváracej sviečky: málo stupňov voľnosti, prahy v ATR."""

    NOTE: ClassVar[str] = (
        "Typ príkazu (`orderType`) a pomer RR sú dve rozhodnutia, ktoré menia stratégiu "
        "najviac — market a limit sú v podstate dve stratégie s tým istým signálom. Lad ich "
        "ako prvé a zvlášť; prahy filtrov až potom, ak vôbec."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        # Dva profily toho istého signálu; rozdiel medzi nimi je väčší než ladenie prahov.
        "orderType": {"choices": ["market", "limit"]},
        # Jediný parameter, ktorý mení štruktúru obchodu, nie filter.
        "rrRatio": {"low": 0.5, "high": 4.0, "step": 0.25},
        # Ako dlho po otvorení má prerazenie ešte zmysel.
        "entryWindowMinutes": {"low": 15, "high": 240, "step": 15},
        # Ako hlboko pod sviečku ide stop — mení R a tým aj winrate.
        "slBufferAtr": {"low": 0.0, "high": 0.5, "step": 0.05, "unit": "atr"},
        # Smer: na indexoch býva long a short iná stratégia.
        "tradeDirection": {"choices": ["Both", "Long only", "Short only"]},
    }

    #: Ktorý parameter robí staticky to, čo model mení za behu.
    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR); riziko na obchod sa nemení"),
        "sl": ("slBufferAtr", "ako hlboko pod otváraciu sviečku ide stop; veľkosť sa dopočíta "
                              "tak, aby riziko na obchod ostalo rovnaké"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slBufferAtr",
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "hour": "entryWindowMinutes",
        "exit_reason": "closeAtSessionEnd",
        "duration_min": "limitValidMinutes",
        "regime_align": "orderType",
        "regime_trend": "maxRangePct",
    }

    WARN: ClassVar[dict[str, str]] = {
        "minClosePosPct": "filter citlivosti, nie štruktúra obchodu — ladí sa ľahko a prefituje ešte ľahšie",
        "breakBufferAtr": "to isté: malý prah s veľkým vplyvom na počet obchodov",
        "volMultiplier": "objemový filter na CFD nie je porovnateľný medzi brokermi; nechaj ho vypnutý",
        "sessionStartH": "otvorenie seansy nie je parameter, je to fakt o trhu",
        "maxTradesPerDay": "strop, nie signál — ladením sa z neho stane skrytý filter dní",
        "openingMinutes": "mení, čo stratégia vôbec je; porovnaj 5 a 15 ako dva behy, nelaď to",
    }
