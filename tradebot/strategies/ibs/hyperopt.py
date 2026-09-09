"""Čo o ladení IBS vieme — odporúčania, varovania a väzby medzi parametrami.

Všetko tu je zápis merania [docs/merania/HYPEROPT_btcusdt_2026-09-04.md], nie odhad.
Prvá verzia priestoru ladila desať prahov v jednotke `atr` plus prepínače entry modelov
a dopadla presne tak, ako sa to pri desiatich stupňoch voľnosti a ~150 obchodoch za rok
dá čakať: víťazná epocha bola na ladenom roku +34,8 %, ale **všetky štyri** out-of-sample
roky boli stratové (−11 % až −65 %).

Čo naopak prežilo naprieč piatimi rokmi, boli zmeny s jedným stupňom voľnosti: `rrRatio`,
`slLookback` a zapnutie štruktúrneho filtra. Preto sú odporúčané práve tie — a k nim
`structureSwingLen`, ktorý sa nikdy neladil, hoci filter, ktorý ho používa, je najsilnejšia
páka, akú sme našli.
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["IBSHyperopt"]


class IBSHyperopt(StrategyHyperopt):
    """Ladenie IBS: málo stupňov voľnosti, prahy v `atr`, okno seansy zvlášť."""

    NOTE: ClassVar[str] = (
        "Menej je viac: na IBS prežili out-of-sample len zmeny s jedným stupňom voľnosti. "
        "Ladenie desiatich prahov naraz dalo +34,8 % na ladenom roku a stratu vo všetkých "
        "štyroch ostatných (docs/merania/HYPEROPT_btcusdt_2026-09-04.md)."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        # Prežilo päť rokov: pomer TP k SL je jediný parameter, ktorý mení štruktúru
        # obchodu a nie citlivosť filtra.
        "rrRatio": {"low": 2.0, "high": 8.0, "step": 0.5},
        # Ako daleko spätne sa hľadá swing pre SL. Druhá zmena, ktorá prežila.
        "slLookback": {"low": 5, "high": 40},
        # Štruktúrny filter je najsilnejšia páka, ktorú sme našli — a jeho vlastná
        # dĺžka swingu sa nikdy neladila.
        "structureSwingLen": {"low": 3, "high": 25},
        "useStructureFilter": {"choices": [False, True]},
        # Filter tesných SL: poplatok je percento z nominálu, zisk rastie s R.
        # V `pct`, nie v cenových bodoch — inak neplatí na inom trhu.
        "minSlDistance": {"low": 0.0, "high": 0.6, "step": 0.05, "unit": "pct"},
    }

    #: Ktorý parameter riadi ktorú vlastnosť obchodu — analytika podľa toho vie povedať
    #: nielen „táto skupina kazí výsledok", ale aj čím sa dá odstrániť.
    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "minSlDistance",        # tesné stopy sa dajú odfiltrovať prahom
        "rr_planned": "rrRatio",          # plánovaný pomer TP k SL
        "direction": "tradeDirection",    # keď edge nesie jedna strana
        "hour": "sess2TradeStartH",       # celý edge bol v NY seanse
        "exit_reason": "closeAtSessionEnd",  # výstupy na čas riadi tento prepínač
        "duration_min": "state2MaxBars",  # ako dlho sa čaká na potvrdenie
    }

    WARN: ClassVar[dict[str, str]] = {
        "minImbSizePoints": "prah v cenových bodoch; na hyperopte sa prefitoval — ak už, tak v jednotke atr",
        "pbMinRangePoints": "to isté ako minImbSizePoints — prah citlivosti, nie štruktúra obchodu",
        "engMinRangePoints": "to isté ako minImbSizePoints — prah citlivosti, nie štruktúra obchodu",
        "srClusterPoints": "prah v cenových bodoch, prefitoval sa",
        "liqSweepMinWick": "prah v cenových bodoch, prefitoval sa",
        "ewMinWavePoints": "prah v cenových bodoch, prefitoval sa",
        "enableImbEntry": "vypnutie entry modelu ubere väčšinu obchodov; výsledok potom nie je čím podložiť",
        "enablePinBarEntry": "prepínač entry modelu — v pôvodnom priestore patril k tým, čo sa prefitovali",
        "enableEngulfingEntry": "prepínač entry modelu — v pôvodnom priestore patril k tým, čo sa prefitovali",
        "sess2TradeStartH": "okno NY seansy nesie celý edge; ladiť sa dá, ale len celé hodiny a s rozmyslom",
        "sess2TradeEndH": "okno NY seansy nesie celý edge; ladiť sa dá, ale len celé hodiny a s rozmyslom",
    }

    @classmethod
    def constrain(cls, cfg) -> None:
        """Obchodné okná musia mať kladnú dĺžku.

        Hyperopt väzbu medzi dvoma parametrami vyjadriť nevie — začiatok a koniec okna
        vyberá nezávisle, takže polovica kombinácií by dávala okno dĺžky nula alebo
        zápornej. Taká vetva priestoru nemá ani jeden obchod a optimalizátor v nej blúdi
        naslepo, namiesto aby videl, či je okno nastavené dobre.
        """
        for zac, kon in (("sess1TradeStartH", "sess1TradeEndH"),
                         ("sess2TradeStartH", "sess2TradeEndH"),
                         ("sess3TradeStartH", "sess3TradeEndH")):
            start, end = getattr(cfg, zac, None), getattr(cfg, kon, None)
            if start is None or end is None:
                continue
            if end <= start:
                setattr(cfg, kon, min(int(start) + 1, 23))
