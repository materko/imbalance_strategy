"""Čo o ladení divergenčnej stratégie vieme.

Rozsahy sú okolie hodnôt, ktoré pôvodná stratégia dostala z hyperoptu v roku 2022
(`prd` 3–7, `maxBars` 100–200, `maxPp` 10) — teda odhad z vtedajšieho merania, nie
z dnešného. Kým nie je analytika (`docs/ANALYTIKA.md`), ber ich ako východisko.
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["DivergenceHyperopt"]


class DivergenceHyperopt(StrategyHyperopt):
    NOTE: ClassVar[str] = (
        "Najsilnejsia paka je, KTORE indikatory sa pocitaju a kolko ich musi suhlasit "
        "(minDivs*); az potom perioda pivotu. Filtre trendu (supertrend na 1h/4h) a zonovy "
        "filter rozhoduju o pocte obchodov viac nez cokolvek na vystupe."
    )

    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR); 0 = bez pevného cieľa"),
        "sl": ("slAtrMult", "vzdialenosť stopu; veľkosť sa dopočíta tak, aby riziko "
                            "na obchod ostalo rovnaké"),
    }

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "prd": {"low": 3, "high": 9},
        "searchDiv": {"choices": ["regular", "hidden", "regular/hidden"]},
        "minDivsLong": {"low": 1, "high": 4},
        "minDivsShort": {"low": 1, "high": 4},
        "maxBars": {"low": 60, "high": 300, "step": 20},
        "stMultHtf": {"low": 2.0, "high": 5.0, "step": 0.5},
        "stMult": {"low": 2.0, "high": 6.0, "step": 0.5},
        "rsiLongMax": {"low": 50, "high": 75, "step": 5},
        "rsiShortMin": {"low": 25, "high": 50, "step": 5},
        "slAtrMult": {"low": 1.0, "high": 5.0, "step": 0.5},
        "rrRatio": {"low": 0.0, "high": 6.0, "step": 0.5},
        "trailActivationPct": {"low": 1.0, "high": 8.0, "step": 0.5},
        "trailOffsetPct": {"low": 0.3, "high": 3.0, "step": 0.1},
        "zoneWindow2": {"low": 6, "high": 60, "step": 6},
        "zoneSearchDiv": {"choices": ["regular", "hidden", "regular/hidden"]},
        "entryMode": {"choices": ["confirm", "immediate"]},
    }

    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slAtrMult",
        "rr_planned": "rrRatio",
        "direction": "tradeDirection",
        "duration_min": "trailOffsetPct",
    }

    WARN: ClassVar[dict[str, str]] = {
        "riskDollar": "riziko na obchod nemení edge, len veľkosť pozície — break-even od neho nezávisí",
        "leverage": "páka nemení signály; ovplyvní len to, či sa pozícia zmestí na účet",
        "maxPp": "s viac pivotmi pribúdajú hlavne staré divergencie — spolu s maxBars sa na tom "
                 "hyperopt rád prefituje",
        "htfMinutes": "musí byť násobkom TF grafu, inak config engine odmietne",
        "htf2Minutes": "musí byť násobkom TF grafu a aspoň htfMinutes",
        "zoneMaxBars": "zóny sa počítajú na vyšších TF — 200 barov 4h je viac než mesiac histórie, "
                       "čo predlžuje rozbeh každého behu",
        "maxHoldBars": "časový limit je v baroch, naladený na jednom TF na inom znamená iný obchod",
    }

    @classmethod
    def constrain(cls, cfg) -> None:
        """Väzby, ktoré hyperopt sám nevie: druhý HTF nad prvým, zámok pod aktiváciou."""
        if int(cfg.htf2Minutes) < int(cfg.htfMinutes):
            cfg.htf2Minutes = int(cfg.htfMinutes)
        if cfg.enableTrailing and cfg.beActivationPct > 0 and cfg.beLockPct >= cfg.beActivationPct:
            cfg.beLockPct = round(float(cfg.beActivationPct) / 4.0, 3)
