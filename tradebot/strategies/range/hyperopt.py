"""Čo o ladení Range Breakoutu vieme — odporúčania, varovania, väzby.

Stratégia je nová (2026-09-11), takže tu zatiaľ nie je zápis merania ako pri IBS, ale
poučenie z neho: priestor je zámerne úzky. Na IBS dopadlo ladenie desiatich prahov naraz
tak, že víťazná epocha bola na ladenom roku +34,8 % a všetky štyri out-of-sample roky
stratové (docs/merania/HYPEROPT_btcusdt_2026-09-04.md). Preto sú odporúčané len parametre,
ktoré menia **štruktúru obchodu**, nie citlivosť filtra.
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["RangeHyperopt"]


class RangeHyperopt(StrategyHyperopt):
    """Ladenie range breakoutu: málo stupňov voľnosti, prahy v ATR."""

    NOTE: ClassVar[str] = (
        "Tesnosť konsolidácie (`maxWidthAtr`) a typ vstupu (`entryMode`) sú dve rozhodnutia, "
        "ktoré menia stratégiu najviac — ostatné sú jemné doladenie. Lad ich ako prvé a zvlášť."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        # Ako tesná musí konsolidácia byť — hlavná páka na kvalitu setupu.
        "maxWidthAtr": {"low": 1.0, "high": 3.0, "step": 0.25, "unit": "atr"},
        # Dĺžka okna: koľko histórie sa na range pozerá.
        "lookbackBars": {"low": 8, "high": 30},
        # Pomer TP k SL — jediný parameter, ktorý mení štruktúru obchodu, nie filter.
        "rrRatio": {"low": 1.0, "high": 4.0, "step": 0.25},
        # Tri profily toho istého nápadu; rozdiel medzi nimi je väčší než ladenie prahov.
        "entryMode": {"choices": ["close", "retest", "continuation"]},
        # Kam presne ide stop v rámci rangu.
        "slRangePct": {"low": 20.0, "high": 100.0, "step": 10.0},
    }

    #: Ktorý parameter robí staticky to, čo model mení za behu.
    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR); riziko na obchod sa nemení"),
        "sl": ("slRangePct", "ako hlboko do rangu ide stop; veľkosť sa dopočíta tak, aby "
                             "riziko na obchod ostalo rovnaké"),
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slRangePct",
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "hour": "tradeStartH",
        "exit_reason": "maxHoldBars",
        "duration_min": "maxRangeAgeBars",
        "regime_align": "entryMode",
        "regime_trend": "maxWidthAtr",
    }

    WARN: ClassVar[dict[str, str]] = {
        "minClosePosPct": "filter citlivosti, nie štruktúra obchodu — ladí sa ľahko a prefituje ešte ľahšie",
        "breakBufferAtr": "to isté: malý prah s veľkým vplyvom na počet obchodov",
        "cooldownBars": "technický parameter, nie edge; nechaj ho tak",
        "confirmMaxBars": "má zmysel len pri entryMode=continuation, inak sa ladí naprázdno",
        "maxTradesPerDay": "strop, nie signál — laděním sa z neho stane skrytý filter dní",
    }
