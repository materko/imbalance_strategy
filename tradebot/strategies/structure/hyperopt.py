"""Čo o ladení stratégie štruktúry vieme — a hlavne, čo o nej vie len ona.

Typy a rozsahy si generický hyperopt prečíta z configu; tu sú tri veci, ktoré z configu
vyčítať nejde:

1. `SUGGESTED` — že `entryMode` je enum s tromi hodnotami, vie config. Že je to
   **najsilnejšia páka celej stratégie** — tri rôzne tvrdenia o trhu na tej istej
   štruktúre —, vie len stratégia. Preto je prvý.
2. `FEATURE_PARAMS` — ktorý parameter riadi ktorú vlastnosť obchodu, aby analytika
   nekončila zistením „obchody s tesným stopom nezarábajú", ale odkazom na parameter.
3. `constrain` — väzby, ktoré hyperopt sám vyjadriť nevie. Tu je jedna a je skutočná:
   rovnaký začiatok a koniec okna znamená nulové okno a nula obchodov; config to
   odmietne a celá vetva priestoru by bola diera, v ktorej optimalizátor blúdi naslepo.

Rozsahy sú **rozumné okolie defaultu**, nie výsledok merania — meranie za sebou zatiaľ
nemáme (viď `docs/ANALYTIKA.md` v tomto balíku). Kto ich berie ako odporúčanie, berie
ako odporúčanie odhad.
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["StructureHyperopt"]


class StructureHyperopt(StrategyHyperopt):
    """Ladenie štruktúry: najprv variant vstupu, až potom čísla."""

    NOTE: ClassVar[str] = (
        "Najprv `entryMode` (choch / bos / sweep) — su to tri rozne tvrdenia o trhu a rozdiel "
        "medzi nimi byva vacsi nez cokolvek, co sa da nasledne doladit. Ladit cisla skor, nez "
        "je jasne, ktory variant vobec drzi, znamena doladit ten nespravny."
    )

    #: Čo smie meniť model AI vrstvy a ktorý parameter to isté drží staticky.
    #: `sl` je tu `slAtrMult`, nie `slBuffer`: rezerva za swingom posúva stop len
    #: o kúsok, kým násobok ATR určuje celú jeho vzdialenosť — a práve tú model mení.
    AI_ADJUSTABLE = {
        "size": ("riskDollar", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("rrRatio", "vzdialenosť take profitu (RR); riziko na obchod sa nemení"),
        "sl": ("slAtrMult", "vzdialenosť stopu; veľkosť sa dopočíta tak, aby riziko "
                            "na obchod ostalo rovnaké"),
    }

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        # Tri varianty tej istej štruktúry. Nie je to citlivosť filtra, je to iná myšlienka.
        "entryMode": {"choices": ["choch", "bos", "sweep"]},
        # Čím sa obchod končí: pevné RR, alebo ďalšia udalosť štruktúry. Druhá najsilnejšia páka.
        "exitMode": {"choices": ["rr", "structure"]},
        # Koľko barov vpravo musí swing prežiť — mení, čo ešte je štruktúra a čo šum,
        # a zároveň to je oneskorenie signálu.
        "swingRight": {"low": 2, "high": 12},
        "swingLeft": {"low": 2, "high": 12},
        # Pomer TP k SL mení štruktúru obchodu, nie citlivosť filtra.
        "rrRatio": {"low": 1.0, "high": 6.0, "step": 0.5},
        # Filter šumu: aká dlhá musí byť noha, aby sa swing rátal. Prenositeľné (atr).
        "minSwingSize": {"low": 0.0, "high": 2.0, "step": 0.25, "unit": "atr"},
        # Rezerva za swingom — tesné stopy majú najhorší pomer edge k poplatku.
        "slBuffer": {"low": 0.0, "high": 0.6, "step": 0.05, "unit": "atr"},
    }

    #: Vlastnosť obchodu -> parameter, ktorým sa dá zmeniť (`tester/analytics.py`).
    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slBuffer",         # kam sa dá stop za swing; v režime atr `slAtrMult`
        "rr_planned": "rrRatio",      # plánovaný pomer TP k SL
        "direction": "tradeDirection",  # keď celý edge nesie jedna strana
        "duration_min": "exitMode",   # čím obchod končí: RR, štruktúra alebo čas
        "hour": "useSession",         # keď je edge len v časti dňa
    }

    WARN: ClassVar[dict[str, str]] = {
        "riskDollar": "riziko na obchod nemení edge, len veľkosť pozície — break-even "
                      "poplatok od neho nezávisí, takže sa ladiť nemá čo",
        "leverage": "páka nemení signály; ovplyvní len to, či sa pozícia zmestí na účet",
        "maxBars": "časový limit je v baroch, takže naladený na jednom TF na inom znamená "
                   "iný obchod; pred ladením si over, že ho stratégia vôbec potrebuje "
                   "(bez neho je 0 = vypnutý)",
        "atrLen": "mení naraz VŠETKY prahy zadané v jednotke atr — vyzerá ako jeden "
                  "parameter, ale posúva celý priestor a hyperopt sa na ňom rád prefituje",
    }

    @classmethod
    def constrain(cls, cfg) -> None:
        """Nulové obchodné okno je diera bez obchodov — posunieme koniec o hodinu."""
        if getattr(cfg, "useSession", False) and cfg.sessionStartH == cfg.sessionEndH:
            cfg.sessionEndH = (int(cfg.sessionStartH) + 1) % 24
